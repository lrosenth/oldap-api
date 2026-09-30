"""Read-only acceptance and bounded load on an existing Linux Docker deployment.

Run on the Docker host with Python and requests; no container/config changes.
Replay a private catalog from read_performance through the API container IP,
excluding TLS/WAN overhead. Only anonymous login and known read routes are
allowed. Fixed SELECT fingerprints bracket the entire run. Tokens and response
bodies stay in memory. Process CPU includes unrelated concurrent service work.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import time

import requests

import read_load as load


def validate_case(case):
    """Reject mutation routes and ambiguous paths before sending any request."""
    method, path = case["method"], case["path"]
    get_ok = (
        re.fullmatch(r"/data/fasnacht/[A-Za-z0-9_:./-]+", path)
        or re.fullmatch(r"/admin/hlist/fasnacht/[A-Za-z0-9_-]+", path)
        or path in ("/admin/datamodel/fasnacht", "/admin/datamodel/shared")
        or re.fullmatch(r"/data/textsearch/fasnacht\?q=[A-Za-z0-9]+&limit=25", path)
    )
    post_ok = path in ("/data/search/fasnacht", "/data/summaries/fasnacht")
    if not ((method == "GET" and get_ok and "body" not in case)
            or (method == "POST" and post_ok and isinstance(case.get("body"), dict))):
        raise ValueError("Catalog contains an operation outside the read boundary")
    if ".." in path:
        raise ValueError("Relative path traversal is not allowed")


class ReadSession(requests.Session):
    """Allow only exact catalog requests and anonymous token issuance.

    Redirects and environment proxies are disabled so credentials and requests
    cannot escape the selected API origin. POST bodies must match the catalog.
    """

    def __init__(self, api, cases):
        super().__init__()
        self.trust_env = False
        self.allowed = {("POST", api + "/admin/auth/unknown", "{}")}
        for case in cases:
            validate_case(case)
            self.allowed.add((case["method"], api + case["path"],
                              json.dumps(case.get("body"), sort_keys=True)))

    def request(self, method, url, **kwargs):
        """Validate the full request before invoking the HTTP transport."""
        key = (method.upper(), url, json.dumps(kwargs.get("json"), sort_keys=True))
        if key not in self.allowed or kwargs.get("data") or kwargs.get("params"):
            raise RuntimeError("Request outside the exact read catalog")
        kwargs["allow_redirects"] = False
        kwargs.setdefault("timeout", (3, 10))
        return super().request(method, url, **kwargs)


def docker_inventory():
    """Return non-secret container identity, IP, versions and worker arguments."""
    result = {}
    for name in ("oldap-api", "graphdb", "redis"):
        info = json.loads(subprocess.check_output(["docker", "inspect", name], text=True))[0]
        networks = info["NetworkSettings"]["Networks"]
        addresses = [n["IPAddress"] for n in networks.values() if n.get("IPAddress")]
        if len(addresses) != 1:
            raise RuntimeError("Expected exactly one container network address")
        result[name] = {"id": info["Id"], "image": info["Config"]["Image"],
                        "image_id": info["Image"], "ip": addresses[0],
                        "started_at": info["State"]["StartedAt"],
                        "restarts": info["RestartCount"]}
    code = ('import os,json,importlib.metadata as m; '
            'print(json.dumps({"api":m.version("oldap-api"),'
            '"oldaplib":m.version("oldaplib"),'
            '"gunicorn_args":os.getenv("GUNICORN_CMD_ARGS")}))')
    result["runtime"] = json.loads(subprocess.check_output(
        ["docker", "exec", "oldap-api", "python", "-c", code], text=True))
    result["host_cpus"] = os.cpu_count()
    return result


def process_ids():
    """Identify all existing worker/master and database/cache processes."""
    result = {"load_client": os.getpid()}
    for container, prefix in (("oldap-api", "api"), ("graphdb", "graphdb"), ("redis", "redis")):
        lines = subprocess.check_output(
            ["docker", "top", container, "-eo", "pid"], text=True).splitlines()[1:]
        for line in lines:
            pid = int(line.strip())
            result[f"{prefix}_{pid}"] = pid
    return result


def process_snapshot(pids):
    """Read Linux cumulative CPU/RSS; fail if any service process is replaced."""
    if process_ids() != pids:
        raise RuntimeError("Service process identities changed during measurement")
    result = {}
    for name, pid in pids.items():
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        result[name] = {
            "cpu_seconds": (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK"),
            "rss_mib": int(fields[21]) * os.sysconf("SC_PAGE_SIZE") / 1024**2,
        }
    return result


def fingerprint(db):
    """Hash explicit named-graph bindings with one fixed, bounded SELECT."""
    with requests.Session() as session:
        session.trust_env = False
        response = session.post(db + "/repositories/oldap", data={
            "query": "SELECT ?g ?s ?p ?o WHERE { GRAPH ?g { ?s ?p ?o } }",
            "infer": "false", "timeout": "15",
        }, headers={"Accept": "application/sparql-results+json"},
            timeout=(3, 20), allow_redirects=False)
        response.raise_for_status()
        rows = response.json()["results"]["bindings"]
    return {"bindings": len(rows), "sha256": load.baseline.digest(
        sorted(json.dumps(row, sort_keys=True) for row in rows))}


def read_case(session, api, case):
    """Time transfer, then validate JSON; never retain the response body."""
    started = time.perf_counter()
    response = session.request(case["method"], api + case["path"], json=case.get("body"))
    elapsed = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    value = response.json()
    return {"ms": elapsed, "status": response.status_code, "bytes": len(response.content),
            "hash": load.content_hash(value),
            "resources": len(value["resources"]) if isinstance(value, dict)
            and isinstance(value.get("resources"), list) else None,
            "items": len(value) if isinstance(value, (list, dict)) else None}


def main():
    """Preflight/serial reads, bounded ramp and final preservation verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--users", type=int, nargs="+", default=[1, 2, 4, 8, 16, 1])
    args = parser.parse_args()
    if not 20 <= args.seconds <= 60 or not args.users or any(n < 1 or n > 16 for n in args.users):
        parser.error("Use 20..60 seconds and 1..16 users per stage")
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    catalog = json.loads(args.catalog.read_text())
    for case in catalog:
        validate_case(case)
    cases = {c["id"]: c for c in catalog}
    needed = {key for flow in load.WORKFLOWS.values() for key in flow}
    if not needed <= cases.keys():
        raise ValueError("Catalog lacks required workflow cases")
    inventory = docker_inventory()
    api = "http://" + inventory["oldap-api"]["ip"] + ":8000"
    db = "http://" + inventory["graphdb"]["ip"] + ":7200"
    load.baseline.API = api
    pids = process_ids()
    inventory.update(started_utc=datetime.now(timezone.utc).isoformat(), pids=pids,
                     catalog_sha256=load.baseline.digest(catalog), stages=args.users,
                     seconds=args.seconds, cycle=load.CYCLE, workflows=load.WORKFLOWS,
                     think_seconds=[.5, 1.5], serial_samples=12)
    (args.output / "inventory.json").write_text(json.dumps(inventory, indent=2))
    before = fingerprint(db)
    (args.output / "fingerprint-before.json").write_text(json.dumps(before, indent=2))
    sessions, stages, serial = [], [], {}
    try:
        for _ in range(max(args.users)):
            session = ReadSession(api, catalog)
            sessions.append(session)
            response = session.post(api + "/admin/auth/unknown", json={})
            response.raise_for_status()
            session.headers["Authorization"] = "Bearer " + response.json()["accessToken"]
        references = {}
        for case in catalog:
            first = read_case(sessions[0], api, case)
            references[case["id"]] = first["hash"]
            rows = []
            for _ in range(12):
                row = read_case(sessions[0], api, case)
                if row["hash"] != first["hash"] or row["ms"] > 5000:
                    raise RuntimeError("Serial content mismatch or latency guard exceeded")
                rows.append(row)
            serial[case["id"]] = {"preflight": first, "requests": rows,
                                    "summary": load.stats([r["ms"] for r in rows])}
            (args.output / "serial.json").write_text(json.dumps(serial, indent=2))
            print(json.dumps({"case": case["id"], **serial[case["id"]]["summary"]}), flush=True)
        selected = {key: cases[key] for key in sorted(needed)}
        references = {key: references[key] for key in selected}
        for index, users in enumerate(args.users):
            stage = load.run_stage(users, args.seconds, selected, sessions, references,
                                   pids, snapshot=process_snapshot)
            stage["summary"]["stage"] = index
            stages.append(stage["summary"])
            (args.output / f"stage-{index}.json").write_text(json.dumps(stage, indent=2))
            print(json.dumps(stage["summary"]), flush=True)
            if stage["summary"]["aborted"] or stage["summary"]["requests"].get("p95_ms", 0) > 2000:
                break
            time.sleep(3)
    finally:
        for session in sessions:
            session.close()
        after = fingerprint(db)
        final_inventory = docker_inventory()
        summary = {"stages": stages, "fingerprint_before": before,
                   "fingerprint_after": after, "data_unchanged": before == after,
                   "container_identity_unchanged": all(
                       inventory[n] == final_inventory[n] for n in ("oldap-api", "graphdb", "redis")),
                   "finished_utc": datetime.now(timezone.utc).isoformat()}
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps({k: v for k, v in summary.items() if k != "stages"}), flush=True)
        if before != after:
            raise RuntimeError("Explicit named-graph fingerprint changed")


if __name__ == "__main__":
    main()
