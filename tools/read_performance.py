"""Sequential read-only OLDAP baseline and isolated request profiling.

Run with the native API's Python environment from the repository root. This
diagnostic uses factory() to isolate request profiling from normal process
startup and prefix bootstrap. No service is restarted or cache cleared. Only
existing data are selected.
Tokens and response bodies are never written to measurement artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import cProfile
from datetime import datetime, timezone
import functools
import hashlib
import importlib.metadata
import inspect
import json
import logging
import math
import os
from pathlib import Path
import platform
import pstats
import re
import statistics
import subprocess
import sys
import time
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB = "http://localhost:7200"
API = "http://localhost:8000"
QUERY_URL = DB + "/repositories/oldap"


def digest(value):
    """Hash canonical JSON without persisting its potentially private contents."""
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class Recorder:
    """Record nested wall times with exclusive buckets that never double count."""

    def __init__(self):
        self.active = None
        self.stack = []
        self.queries = {}

    @contextmanager
    def span(self, name):
        if self.active is None:
            yield
            return
        frame = [name, time.perf_counter(), 0.0]
        self.stack.append(frame)
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - frame[1]) * 1000
            self.stack.pop()
            if self.stack:
                self.stack[-1][2] += elapsed
            item = self.active["spans"].setdefault(
                name, {"count": 0, "inclusive_ms": 0, "exclusive_ms": 0}
            )
            item["count"] += 1
            item["inclusive_ms"] += elapsed
            item["exclusive_ms"] += elapsed - frame[2]

    def wrap(self, owner, attribute, label):
        """Preserve method descriptor semantics while measuring one boundary."""
        descriptor = inspect.getattr_static(owner, attribute)
        function = (
            descriptor.__func__
            if isinstance(descriptor, (classmethod, staticmethod))
            else descriptor
        )

        @functools.wraps(function)
        def measured(*args, **kwargs):
            with self.span(label):
                value = function(*args, **kwargs)
            if label == "cache.get" and self.active is not None:
                self.active["cache_hits" if value is not None else "cache_misses"] += 1
            return value

        replacement = (
            type(descriptor)(measured)
            if isinstance(descriptor, (classmethod, staticmethod))
            else measured
        )
        setattr(owner, attribute, replacement)


def install_transport_guard(recorder, *, api_url=API):
    """Allow only local query/metadata and explicitly catalogued API reads.

    Validate SPARQL once per exact query outside measured transport time. The
    parser accepts queries, never SPARQL Update. SERVICE and connector control
    predicates are prohibited as additional protections against side effects.
    """
    from rdflib.plugins.sparql.parser import parseQuery

    original = requests.sessions.Session.request
    validated = set()

    def guarded(session, method, url, **kwargs):
        parsed = urlsplit(url)
        method = method.upper()
        query = None
        if url == QUERY_URL and method == "POST":
            data = kwargs.get("data", {})
            if not isinstance(data, dict) or "query" not in data or "update" in data:
                raise RuntimeError("Only SPARQL query form posts are allowed")
            query = data["query"]
            key = hashlib.sha256(query.encode()).hexdigest()
            if key not in validated:
                if re.search(
                    r"\bSERVICE\b|luc:(?:create|drop)|connectors/lucene#(?:create|drop)",
                    query,
                    re.I,
                ):
                    raise RuntimeError("Remote or connector-control query blocked")
                # Parsing is safety instrumentation, recorded separately.
                with recorder.span("guard.validation"):
                    # RDFLib's SPARQL parser lacks RDF-star quoted triples.
                    # Replace only those terms in the validation copy; GraphDB
                    # receives the original query, including its ACL patterns.
                    validation_query = re.sub(
                        r"<<[^\n]*?>>", "<urn:benchmark:quoted-triple>", query
                    )
                    parseQuery(validation_query)
                validated.add(key)
            recorder.queries[key] = query
            kwargs["data"] = {**data, "timeout": "15"}
        elif url.startswith(DB + "/rest/") and method == "GET":
            pass
        elif (
            parsed.scheme == "http"
            and parsed.hostname == "localhost"
            and parsed.port == urlsplit(api_url).port
        ):
            allowed_get = parsed.path in {
                "/health",
                "/status",
                "/admin/datamodel/fasnacht",
                "/admin/datamodel/shared",
            } or parsed.path.startswith(
                (
                    "/data/fasnacht/",
                    "/data/textsearch/fasnacht",
                    "/admin/hlist/fasnacht/",
                )
            )
            allowed_post = parsed.path in {
                "/data/search/fasnacht",
                "/data/summaries/fasnacht",
                "/admin/auth/unknown",
            }
            if not (
                (method == "GET" and allowed_get) or (method == "POST" and allowed_post)
            ):
                raise RuntimeError("API operation outside read-only catalog")
        else:
            raise RuntimeError("Network operation outside local read-only boundary")
        kwargs.setdefault("timeout", (3, 20))
        started = time.perf_counter()
        with recorder.span("graphdb.http" if query else "other.http"):
            response = original(session, method, url, **kwargs)
        if query and recorder.active is not None:
            recorder.active["queries"].append(
                {
                    "sha256": key,
                    "ms": (time.perf_counter() - started) * 1000,
                    "bytes": len(response.content),
                    "status": response.status_code,
                }
            )
        return response

    requests.sessions.Session.request = guarded


def query_rows(query):
    """Execute a bounded explicit-data inventory SELECT; return plain bindings."""
    response = requests.post(
        QUERY_URL,
        data={"query": query, "infer": "false"},
        headers={"Accept": "application/sparql-results+json"},
    )
    response.raise_for_status()
    return [
        {key: value["value"] for key, value in row.items()}
        for row in response.json()["results"]["bindings"]
    ]


def fingerprint():
    """Hash all explicit named-graph bindings in memory; never save RDF values."""
    response = requests.post(
        QUERY_URL,
        data={
            "query": "SELECT ?g ?s ?p ?o WHERE { GRAPH ?g { ?s ?p ?o } }",
            "infer": "false",
        },
        headers={"Accept": "application/sparql-results+json"},
    )
    response.raise_for_status()
    rows = response.json()["results"]["bindings"]
    return {
        "bindings": len(rows),
        "sha256": digest(sorted(json.dumps(row, sort_keys=True) for row in rows)),
    }


def inventory():
    """Capture actual versions, repository settings, graph counts and hardware."""

    def get(path):
        response = requests.get(DB + path)
        response.raise_for_status()
        return (
            response.json()
            if "json" in response.headers.get("Content-Type", "")
            else response.text
        )

    import oldaplib

    library_root = Path(oldaplib.__file__).parent
    result = {
        "library_source": str(library_root),
        "library_source_hashes": {
            name: hashlib.sha256((library_root / "src" / name).read_bytes()).hexdigest()
            for name in (
                "cachesingleton.py",
                "project.py",
                "datamodel.py",
                "objectfactory.py",
                "mutation_gate.py",
            )
        },
        "at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("oldaplib", "flask", "requests", "rdflib", "redis")
        },
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "graphdb": get("/rest/info/version"),
        "size": get("/rest/repositories/oldap/size"),
        "settings": get("/rest/repositories/oldap"),
        "infrastructure": get("/rest/monitor/infrastructure"),
        "repository_metrics": get("/rest/monitor/repository/oldap"),
        "graphs": query_rows(
            "SELECT ?g (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g ORDER BY DESC(?n)"
        ),
        "classes": query_rows(
            "SELECT ?c (COUNT(?s) AS ?n) WHERE { GRAPH <http://fasnacht.digital/ns/data> { ?s a ?c } } GROUP BY ?c ORDER BY DESC(?n)"
        ),
    }
    if sys.platform == "darwin":
        result["hardware"] = {
            key: subprocess.check_output(["sysctl", "-n", key], text=True).strip()
            for key in (
                "machdep.cpu.brand_string",
                "hw.memsize",
                "hw.physicalcpu",
                "hw.logicalcpu",
            )
        }
    result["git"] = {
        repo: subprocess.check_output(
            ["git", "-C", str(ROOT.parent / repo), "rev-parse", "HEAD"], text=True
        ).strip()
        for repo in ("oldap-api", "oldaplib")
    }
    return result


def install_spans(recorder):
    """Measure stable shared API/library boundaries in this process only."""
    from oldaplib.src.connection import Connection
    from oldaplib.src.project import Project
    from oldaplib.src.datamodel import DataModel
    from oldaplib.src.cachesingleton import CacheSingletonRedis
    from oldaplib.src.objectfactory import ResourceInstanceFactory, ResourceInstance
    from oldaplib.src.helpers.query_processor import QueryProcessor
    from oldaplib.src.helpers.construct_processor import ConstructProcessor
    from oldaplib.src.oldaplist import OldapList
    from rdflib import Graph
    from redis import Redis
    from flask.json.provider import DefaultJSONProvider
    from oldap_api.views import instance_views

    for owner, name, label in [
        (Connection, "__init__", "auth.connection"),
        (Connection, "query", "graphdb.query_decode"),
        (Project, "read", "model.project"),
        (DataModel, "read", "model.datamodel"),
        (CacheSingletonRedis, "get", "cache.get"),
        (CacheSingletonRedis, "set", "cache.set"),
        (Redis, "execute_command", "redis.command"),
        (Redis, "__init__", "redis.client_init"),
        (ResourceInstanceFactory, "__init__", "factory.init"),
        (ResourceInstanceFactory, "read_data", "resource.read"),
        (ResourceInstanceFactory, "read_summaries", "resource.summaries"),
        (ResourceInstance, "search", "search"),
        (ResourceInstance, "search_fulltext", "search.fulltext"),
        (OldapList, "ensure_list_node_context", "model.list_context"),
        (QueryProcessor, "__init__", "results.query_processor"),
        (ConstructProcessor, "process", "results.construct_processor"),
        (Graph, "parse", "results.rdf_parse"),
        (instance_views, "_instance_read_json", "results.api_shape"),
        (instance_views, "_summary_media_delivery", "results.media_delivery"),
        (DefaultJSONProvider, "dumps", "results.json"),
    ]:
        recorder.wrap(owner, name, label)


def request_case(client, case, token, live=False):
    """Execute one catalogued read, returning status, length and JSON payload."""
    headers = {"Authorization": "Bearer " + token}
    if live:
        response = client.request(
            case["method"],
            API + case["path"],
            json=case.get("body"),
            headers=headers,
            timeout=(3, 25),
        )
        return response.status_code, len(response.content), response.json()
    response = client.open(
        case["path"], method=case["method"], json=case.get("body"), headers=headers
    )
    return response.status_code, len(response.data), response.get_json()


def build_cases(client, token):
    """Select real caller-visible examples and a fixed bounded request catalog."""

    def search(cls, limit=25):
        case = {
            "method": "POST",
            "path": "/data/search/fasnacht",
            "body": {"resClass": cls, "limit": limit},
        }
        status, _, value = request_case(client, case, token)
        if status != 200 or not isinstance(value, list) or not value:
            raise RuntimeError(
                f"No readable discovery results for {cls}: status={status}, message={value.get('message') if isinstance(value, dict) else type(value).__name__}"
            )
        return value

    media = search("fasnacht:ArchiveMediaObject", 100)
    people = search("fasnacht:Person", 1)
    units = search("shared:ArchiveUnit", 100)
    cases = []

    def add(name, path, body=None):
        cases.append(
            {
                "id": name,
                "method": "POST" if body is not None else "GET",
                "path": path,
                **({"body": body} if body is not None else {}),
            }
        )

    add("resource_person", "/data/fasnacht/" + people[0]["iri"])
    add("resource_media", "/data/fasnacht/" + media[0]["iri"])
    large = next(
        (item["iri"] for item in units if "bmg-goldenes-buch-1" in item["iri"]),
        units[0]["iri"],
    )
    add("resource_linked_archive", "/data/fasnacht/" + large)
    base = {"resClass": "fasnacht:ArchiveMediaObject", "limit": 25}
    add("search_page1", "/data/search/fasnacht", base)
    add("search_sorted", "/data/search/fasnacht", {**base, "sortBy": ["schema:name"]})
    add(
        "search_offset250",
        "/data/search/fasnacht",
        {**base, "offset": 250, "sortBy": ["schema:name"]},
    )
    add(
        "search_count",
        "/data/search/fasnacht",
        {"resClass": "fasnacht:ArchiveMediaObject", "countOnly": True},
    )
    add("search_fulltext", "/data/textsearch/fasnacht?q=Basel&limit=25")
    add(
        "search_with_properties",
        "/data/search/fasnacht",
        {**base, "includeProperties": ["schema:name", "schema:description"]},
    )
    for count in (25, 100):
        add(
            "summaries_" + str(count),
            "/data/summaries/fasnacht",
            {
                "iris": [item["iri"] for item in media[:count]],
                "includeProperties": ["schema:name", "schema:description"],
            },
        )
    add(
        "summaries_25_delivery",
        "/data/summaries/fasnacht",
        {
            "iris": [item["iri"] for item in media[:25]],
            "includeProperties": ["schema:name"],
            "includeMediaDelivery": True,
        },
    )
    parents = query_rows(
        "SELECT ?parent (COUNT(?s) AS ?n) WHERE { GRAPH <http://fasnacht.digital/ns/data> { ?s <http://oldap.org/shared#parentArchiveUnit> ?parent } } GROUP BY ?parent ORDER BY DESC(?n) LIMIT 1"
    )
    if parents:
        add(
            "archive_children",
            "/data/search/fasnacht",
            {
                "resClass": "shared:ArchiveUnit",
                "limit": 25,
                "filter": [
                    {
                        "property": "shared:parentArchiveUnit",
                        "op": "EQ",
                        "value": parents[0]["parent"],
                        "type": "iri",
                    }
                ],
            },
        )
    lists = query_rows(
        "SELECT ?s WHERE { GRAPH <http://fasnacht.digital/ns/lists> { ?s a <http://oldap.org/base#OldapList> } } ORDER BY ?s LIMIT 1"
    )
    if lists:
        add(
            "hierarchical_list",
            "/admin/hlist/fasnacht/" + lists[0]["s"].rsplit("/", 1)[-1],
        )
    # These reads live under /admin but also supply ordinary UI field labels.
    add("datamodel_fasnacht", "/admin/datamodel/fasnacht")
    add("datamodel_shared", "/admin/datamodel/shared")
    add(
        "search_lucene_fields",
        "/data/search/fasnacht",
        {
            **base,
            "ftfilter": [
                {"field": "archiveMediaObjectTitle", "query": "Basel"},
                "OR",
                {"field": "archiveMediaObjectDescription", "query": "Basel"},
            ],
            "includeProperties": ["schema:name", "schema:description"],
            "sortBy": ["schema:name|asc"],
        },
    )
    return cases


def summarize(rows):
    """Describe small samples; p95 uses the nearest-rank empirical quantile."""
    groups = defaultdict(list)
    for row in rows:
        groups[(row["subject"], row["case"], row["mode"])].append(row)
    result = []
    for (subject, case, mode), samples in groups.items():
        times = sorted(row["ms"] for row in samples)
        item = {
            "subject": subject,
            "case": case,
            "mode": mode,
            "n": len(samples),
            "median_ms": statistics.median(times),
            "p95_ms": times[max(0, math.ceil(0.95 * len(times)) - 1)],
            "min_ms": min(times),
            "max_ms": max(times),
            "status": dict(Counter(str(row["status"]) for row in samples)),
            "bytes_median": statistics.median(row["bytes"] for row in samples),
        }
        if mode == "instrumented":
            item["query_count_median"] = statistics.median(
                len(row["queries"]) for row in samples
            )
            item["graphdb_http_median_ms"] = statistics.median(
                sum(q["ms"] for q in row["queries"]) for row in samples
            )
            labels = set().union(*(row["spans"] for row in samples))
            item["spans_mean"] = {
                label: {
                    metric: statistics.mean(
                        row["spans"].get(label, {}).get(metric, 0) for row in samples
                    )
                    for metric in ("count", "inclusive_ms", "exclusive_ms")
                }
                for label in labels
            }
            item["cache_hits_mean"] = statistics.mean(
                row["cache_hits"] for row in samples
            )
            item["cache_misses_mean"] = statistics.mean(
                row["cache_misses"] for row in samples
            )
        result.append(item)
    return result


def verify_responses(client, cases, connections):
    """Compare live/isolated payloads without saving response bodies or JWTs.

    RDF property arrays and model class lists have no guaranteed order. Compare
    their content canonically and report root result ordering separately. Media
    capabilities are independently issued JWTs; compare their presence only.
    """

    def normalize(value):
        if isinstance(value, dict):
            return {
                key: bool(item) if key == "capability" else normalize(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return sorted(
                (normalize(item) for item in value),
                key=lambda item: json.dumps(item, sort_keys=True),
            )
        return value

    def order(value):
        values = value.get("resources", []) if isinstance(value, dict) else value
        return (
            [
                item.get("iri")
                for item in values
                if isinstance(item, dict) and "iri" in item
            ]
            if isinstance(values, list)
            else []
        )

    results = []
    with requests.Session() as session:
        for name, connection in connections.items():
            for case in cases:
                live_status, _, live = request_case(
                    session, case, connection.token, live=True
                )
                local_status, _, local = request_case(client, case, connection.token)
                results.append(
                    {
                        "subject": name,
                        "case": case["id"],
                        "live_status": live_status,
                        "inprocess_status": local_status,
                        "content_equal": normalize(live) == normalize(local),
                        "iri_order_equal": order(live) == order(local),
                    }
                )
    return results


def main():
    """Run serial baselines and separate diagnostic profiles; save no credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--discovery-only", action="store_true")
    parser.add_argument(
        "--catalog", type=Path, help="Replay a previously saved cases.json exactly"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Compare live and isolated responses without timed repetitions",
    )
    parser.add_argument(
        "--case", action="append", help="Restrict to named catalog cases (repeatable)"
    )
    args = parser.parse_args()
    if not 1 <= args.samples <= 30:
        parser.error("Use 1..30 sequential samples")
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    load_dotenv(ROOT / ".env.local", override=True)
    os.environ.update(
        OLDAP_TS_SERVER=DB,
        OLDAP_TS_REPO="oldap",
        OLDAP_REDIS_URL="redis://localhost:6379/0",
        APP_ENV="Dev",
        OLDAP_IIIF_SERVER="http://localhost:8182",
        OLDAP_UPLOAD_SERVER="http://localhost:8080",
    )
    recorder = Recorder()
    install_transport_guard(recorder)
    from oldaplib.src.connection import Connection
    from oldap_api.factory import factory
    from oldaplib.src.cachesingleton import CacheSingletonRedis

    # Only normal cache population is allowed; never deletion or a global flush.
    def reject_cache_clear(*args, **kwargs):
        raise RuntimeError("Cache deletion is prohibited by the benchmark")

    CacheSingletonRedis.clear = reject_cache_clear
    CacheSingletonRedis.delete = reject_cache_clear
    logging.disable(logging.CRITICAL)
    before = inventory()
    before["fingerprint"] = fingerprint()
    (args.output / "inventory-before.json").write_text(json.dumps(before, indent=2))
    # A freshly restarted native API has not yet populated its process-local
    # project prefixes. Follow the ordinary anonymous login once, outside all
    # timed requests. It creates no refresh session and writes no RDF data.
    bootstrap = requests.post(API + "/admin/auth/unknown", json={})
    bootstrap.raise_for_status()
    connections = {"unknown": Connection(context_name="DEFAULT")}
    if os.environ.get("OLDAP_AUTH_ADMIN_USER") == "rosenth":
        connections["rosenth"] = Connection(
            userId="rosenth",
            credentials=os.environ["OLDAP_AUTH_ADMIN_PASSWORD"],
            context_name="DEFAULT",
        )
    subjects = {
        name: {
            "user_id": str(con._userdata.userId),
            "roles": {str(k): str(v) for k, v in con._userdata.hasRole.items()},
            "project_permissions": {
                str(k): [str(v) for v in values]
                for k, values in con._userdata.inProject.items()
            },
        }
        for name, con in connections.items()
    }
    (args.output / "subjects.json").write_text(json.dumps(subjects, indent=2))
    app = factory()
    app.config.from_object("oldap_api.config.Dev")
    # The native launcher loads Dev then calls app.run(debug=False).
    # Match its compact JSON formatting and exception handling exactly.
    app.config["DEBUG"] = False
    client = app.test_client()
    cases = (
        json.loads(args.catalog.read_text())
        if args.catalog
        else build_cases(client, connections["unknown"].token)
    )
    for case in cases:
        path = urlsplit(case["path"]).path
        allowed = (
            case["method"] == "POST"
            and path in {"/data/search/fasnacht", "/data/summaries/fasnacht"}
        ) or (
            case["method"] == "GET"
            and (
                path.startswith(
                    (
                        "/data/fasnacht/",
                        "/data/textsearch/fasnacht",
                        "/admin/hlist/fasnacht/",
                    )
                )
                or path in {"/admin/datamodel/fasnacht", "/admin/datamodel/shared"}
            )
        )
        if not allowed:
            raise ValueError("Catalog contains an operation outside the read boundary")
    if args.case:
        missing = set(args.case) - {case["id"] for case in cases}
        if missing:
            raise ValueError("Unknown cases: " + ", ".join(sorted(missing)))
        cases = [case for case in cases if case["id"] in args.case]
    (args.output / "cases.json").write_text(json.dumps(cases, indent=2))
    for case in cases:
        status, size, payload = request_case(client, case, connections["unknown"].token)
        count = (
            len(payload.get("resources", []))
            if isinstance(payload, dict) and "resources" in payload
            else (
                len(payload)
                if isinstance(payload, list)
                else payload.get("count") if isinstance(payload, dict) else None
            )
        )
        print(
            json.dumps(
                {
                    "case": case["id"],
                    "status": status,
                    "bytes": size,
                    "count": count,
                    "error": (
                        payload.get("message") if isinstance(payload, dict) else None
                    ),
                }
            ),
            flush=True,
        )
        if status != 200:
            raise RuntimeError("Catalog preflight failed: " + case["id"])
    if args.discovery_only:
        return
    if args.verify_only:
        results = verify_responses(client, cases, connections)
        (args.output / "response-equivalence.json").write_text(
            json.dumps(results, indent=2)
        )
        after = fingerprint()
        (args.output / "fingerprint-after.json").write_text(json.dumps(after, indent=2))
        if after != before["fingerprint"] or any(
            not item["content_equal"]
            or item["live_status"] != 200
            or item["inprocess_status"] != 200
            for item in results
        ):
            raise RuntimeError("Response equivalence or data fingerprint check failed")
        print(
            "Live and isolated response content matches; data fingerprint unchanged.",
            flush=True,
        )
        return
    rows = []
    stream = (args.output / "samples.jsonl").open("w")
    for mode in ("live_http", "inprocess", "instrumented"):
        if mode == "instrumented":
            install_spans(recorder)
        for name, connection in connections.items():
            for case in cases:
                # Discard a case-specific warmup; shared caches are never reset.
                caller = requests.Session() if mode == "live_http" else client
                request_case(caller, case, connection.token, live=mode == "live_http")
                for index in range(args.samples):
                    row = {
                        "subject": name,
                        "case": case["id"],
                        "mode": mode,
                        "sample": index,
                        "spans": {},
                        "queries": [],
                        "cache_hits": 0,
                        "cache_misses": 0,
                    }
                    recorder.active = row if mode == "instrumented" else None
                    started = time.perf_counter()
                    cpu = time.process_time()
                    with recorder.span("api.request"):
                        status, size, payload = request_case(
                            caller, case, connection.token, live=mode == "live_http"
                        )
                    row.update(
                        ms=(time.perf_counter() - started) * 1000,
                        cpu_ms=(time.process_time() - cpu) * 1000,
                        status=status,
                        bytes=size,
                    )
                    recorder.active = None
                    if status != 200:
                        raise RuntimeError(
                            f"Measured request failed: {case['id']} ({status})"
                        )
                    rows.append(row)
                    stream.write(json.dumps(row) + "\n")
                    stream.flush()
                    time.sleep(0.03)
                if mode == "live_http":
                    caller.close()
                print(
                    mode,
                    name,
                    case["id"],
                    round(statistics.median(r["ms"] for r in rows[-args.samples :]), 2),
                    flush=True,
                )
    stream.close()
    (args.output / "summary.json").write_text(json.dumps(summarize(rows), indent=2))
    # CPU profiler is deliberately separate from latency samples.
    for case in cases:
        name = case["id"]
        if name not in {
            "resource_media",
            "summaries_25",
            "summaries_100",
            "search_page1",
            "datamodel_fasnacht",
            "datamodel_shared",
        }:
            continue
        profile = cProfile.Profile()
        profile.runcall(request_case, client, case, connections["unknown"].token)
        with (args.output / ("profile-" + name + ".txt")).open("w") as file:
            pstats.Stats(profile, stream=file).strip_dirs().sort_stats(
                "cumulative"
            ).print_stats(45)
            pstats.Stats(profile, stream=file).strip_dirs().sort_stats(
                "tottime"
            ).print_stats(25)
    after = inventory()
    after["fingerprint"] = fingerprint()
    (args.output / "inventory-after.json").write_text(json.dumps(after, indent=2))
    (args.output / "queries.json").write_text(json.dumps(recorder.queries, indent=2))
    if before["fingerprint"] != after["fingerprint"]:
        raise RuntimeError(
            "Explicit named-graph fingerprint changed; investigate concurrent changes"
        )
    print("Complete. Explicit named-graph fingerprint unchanged.", flush=True)


if __name__ == "__main__":
    main()
