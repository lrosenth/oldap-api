"""Compare a focused dating CONSTRUCT on an owned Jena preview only.

Uses probe_api_jena's CLI plus --cases, --browser-preview and --fulltext-preview.
The integrated candidate uses its private date reader; the baseline temporarily
selects the original complete summary reader for a sequential comparison. Exact public/audit HTTP responses and native ACL/date
fixtures must match before timing. No production configuration is read or changed.
"""

from contextlib import nullcontext
import json
from pathlib import Path
import runpy
import statistics
import sys
import time
from unittest.mock import patch

import requests
from flask import Flask


def canonical(value):
    """Normalize unordered RDF value lists but retain the outer result order."""

    def normalize(item):
        if isinstance(item, dict):
            return {k: normalize(v) for k, v in sorted(item.items())}
        if isinstance(item, list):
            return sorted(
                (normalize(v) for v in item),
                key=lambda v: json.dumps(v, sort_keys=True),
            )
        return item

    return (
        [normalize(v) for v in value] if isinstance(value, list) else normalize(value)
    )


def exercise(call, con, base, output, public, audit, *, cases):
    """Fail on semantic differences; alternate baseline/candidate on one dataset."""
    from oldap_api.backend import create_connection
    from oldap_api.views import instance_views as views
    from oldaplib.src.objectfactory import (
        ResourceInstanceFactory,
        _dating_insert_triples_for_item,
    )
    from oldaplib.src.xsd.dating import Dating, OldapCalendar, DatePrecision
    from oldaplib.src.xsd.iri import Iri
    from oldaplib.src.xsd.xsd_qname import Xsd_QName

    original_expand = views._expand_search_dating
    original_http = requests.sessions.Session.request
    active = None
    report = {"status": "running", "checks": [], "samples": [], "differences": []}
    report_path = output / "dating-experiment.json"

    def baseline_expand(*args, **kwargs):
        # Compare the integrated path with the original complete summary reader.
        with patch.object(
            ResourceInstanceFactory,
            "_read_search_dating",
            ResourceInstanceFactory.read_summaries,
        ):
            return original_expand(*args, **kwargs)

    def measure_http(session, method, url, **kwargs):
        if active is None or not url.startswith(con._jena.url + "/"):
            return original_http(session, method, url, **kwargs)
        kwargs["headers"] = {**kwargs.get("headers", {}), "X-Probe-Timing": "yes"}
        start = time.perf_counter()
        response = original_http(session, method, url, **kwargs)
        active["calls"].append(
            {
                "ms": (time.perf_counter() - start) * 1000,
                "jena_ms": int(response.headers["X-Probe-Dispatch-Nanos"]) / 1e6,
                "bytes": len(response.content),
            }
        )
        return response

    def read(case, headers, variant, accept="application/json; dating=structured"):
        control = (
            patch.object(views, "_expand_search_dating", baseline_expand)
            if variant == "baseline"
            else nullcontext()
        )
        with control:
            response = requests.post(
                base + case["path"],
                json=case["body"],
                headers={**headers, "Accept": accept},
                timeout=60,
            )
        response.raise_for_status()
        return response

    try:
        # Real export: compare the complete response for every overview request,
        # plus the media date field omitted by the public overview projection.
        extra = {
            "path": "/data/search/fasnacht/class/fasnacht:ArchiveMediaObject",
            "body": {
                "limit": 1000,
                "includeProperties": ["schema:name", "fasnacht:creationDating"],
            },
        }
        for reader, headers in [("public", public), ("audit", audit)]:
            for i, case in enumerate([*cases, extra]):
                for accept in (
                    ["application/json; dating=structured", "application/json"]
                    if i in [7, 9]
                    else ["application/json; dating=structured"]
                ):
                    before = read(case, headers, "baseline", accept).json()
                    after = read(case, headers, "candidate", accept).json()
                    if canonical(before) != canonical(after):
                        label = f"{reader}-{i}-" + (
                            "structured" if "structured" in accept else "legacy"
                        )
                        (output / (label + "-difference.json")).write_text(
                            json.dumps({"before": before, "after": after}, indent=2)
                        )
                        report["differences"].append(label)
                        continue
                    report["checks"].append(
                        f"{reader} case {i} {accept}: complete response and order equal"
                    )

        # Owned synthetic cases exercise permission omissions and connected dates
        # that the real source may not contain. No shared/live RDF is changed.
        from oldaplib.src.helpers.context import Context

        prefix = Context(name=con.context_name).sparql_context
        ns = "urn:dating-experiment:"
        later = Dating((1940,), iri=Iri(ns + "later"))
        early = Dating(
            (1930,),
            (1939,),
            before={later},
            iri=Iri(ns + "early"),
            verbatimDate="[193-?]",
            datePrecision=DatePrecision.DECADE,
            inCalendar=OldapCalendar.GREGORIAN,
        )
        calendar_date = Dating(
            (1930, 2, 1), iri=Iri(ns + "julian"), inCalendar=OldapCalendar.JULIAN
        )
        date_triples = _dating_insert_triples_for_item(
            early, set()
        ) + _dating_insert_triples_for_item(calendar_date, set())
        roots = [
            "public",
            "shared",
            "hidden",
            "restricted",
            "orphanGrant",
            "creator",
            "noDate",
            "dangling",
            "calendar",
            "narrowProperty",
            "multipleTypes",
        ]
        triples = list(date_triples)
        for name in roots:
            subject = "<" + ns + name + ">"
            triples.append(f"{subject} a fasnacht:CarnivalEvent .")
            if name == "multipleTypes":
                triples.append(f"{subject} a fasnacht:CarnivalThing .")
            if name != "noDate":
                date = ns + (
                    "absent"
                    if name == "dangling"
                    else "julian" if name == "calendar" else "early"
                )
                predicate = (
                    f"<{ns}narrowDate>"
                    if name == "narrowProperty"
                    else "fasnacht:dating"
                )
                triples.append(f"{subject} {predicate} <{date}> .")
            if name == "creator":
                triples.append(
                    f"{subject} oldap:createdBy <https://example.org/unknown> ."
                )
                continue
            role = (
                "<urn:dating-experiment:privateRole>"
                if name == "hidden"
                else "oldap:Unknown"
            )
            if name != "orphanGrant":
                triples.append(f"{subject} oldap:attachedToRole {role} .")
            permission = (
                "oldap:DATA_RESTRICTED" if name == "restricted" else "oldap:DATA_VIEW"
            )
            triples.append(
                f"<{ns}grant-{name}> rdf:reifies <<( {subject} oldap:attachedToRole {role} )>> ; oldap:hasDataPermission {permission} ."
            )
        con.update_query(
            prefix
            + "INSERT DATA { GRAPH fasnacht:data { "
            + "\n".join(triples)
            + " } GRAPH fasnacht:onto { <"
            + ns
            + "narrowDate> rdfs:subPropertyOf fasnacht:dating . } }"
        )
        try:
            public_con = create_connection(
                token=public["Authorization"].split(" ", 1)[1]
            )
            factory = ResourceInstanceFactory(con=public_con, project="fasnacht")
            ids = [Iri(ns + n) for n in [*roots, "missing"]]
            properties = {Xsd_QName("fasnacht:dating", validate=False)}
            with Flask(__name__).test_request_context(
                headers={"Accept": "application/json; dating=structured"}
            ):
                baseline = factory.read_summaries(ids, properties)
                slim = factory._read_search_dating(ids, properties)
                wanted = {
                    ns + n
                    for n in [
                        "public",
                        "shared",
                        "creator",
                        "noDate",
                        "dangling",
                        "calendar",
                        "narrowProperty",
                        "multipleTypes",
                    ]
                }
                assert {str(i) for i in baseline} == wanted
                assert set(baseline) == set(slim)
                for iri in baseline:
                    b = views._instance_read_json(baseline[iri]).get("fasnacht:dating")
                    a = views._instance_read_json(slim[iri]).get("fasnacht:dating")
                    assert canonical(b) == canonical(a), str(iri)
                    assert baseline[iri].resource_class == slim[iri].resource_class
                    assert set(baseline[iri].asserted_types) == set(
                        slim[iri].asserted_types
                    )
                value = views._instance_read_json(slim[Iri(ns + "public")])[
                    "fasnacht:dating"
                ][0]
                assert (
                    value["before"] == [ns + "later"]
                    and value["inCalendar"] == "GREGORIAN"
                )
                assert (
                    value["datePrecision"] == "DECADE"
                    and value["verbatimDate"] == "[193-?]"
                )
                # Narrow properties retain the established hydration semantics;
                # importantly, the modeled superproperty must still be returned.
                assert views._instance_read_json(slim[Iri(ns + "narrowProperty")]).get(
                    "fasnacht:dating"
                )
                assert len(slim[Iri(ns + "multipleTypes")].asserted_types) == 2
                calendar_value = views._instance_read_json(slim[Iri(ns + "calendar")])[
                    "fasnacht:dating"
                ][0]
                assert calendar_value["inCalendar"] == "JULIAN"
                assert list(calendar_value["dateStart"]) == [1930, 2, 1]
                report["checks"].append(
                    "Native subproperty/multiple asserted types, public/shared/creator dates, hidden/restricted/orphan-grant/missing omissions, absent date, dangling reference, Julian/decade/verbatim/before: equal"
                )
        finally:
            # Remove only this owned fixture from its two named graphs.
            for graph in ["fasnacht:data", "fasnacht:onto"]:
                con.update_query(
                    prefix + f"DELETE {{ GRAPH {graph} {{ ?s ?p ?o }} }} "
                    f'WHERE {{ GRAPH {graph} {{ ?s ?p ?o FILTER(STRSTARTS(STR(?s), "{ns}")) }} }}'
                )

        assert not report["differences"], report["differences"]
        references = {}
        with patch.object(requests.sessions.Session, "request", measure_http):
            for reader, headers in [("public", public), ("audit", audit)]:
                for phase, variant in [
                    ("warmup", "baseline"),
                    ("warmup", "candidate"),
                ] + [
                    ("timing", v)
                    for v in ["baseline", "candidate", "candidate", "baseline"] * 2
                ]:
                    active = {
                        "reader": reader,
                        "phase": phase,
                        "variant": variant,
                        "calls": [],
                    }
                    start = time.perf_counter()
                    response = read(cases[7], headers, variant)
                    active["http_ms"] = (time.perf_counter() - start) * 1000
                    actual = canonical(response.json())
                    references.setdefault(reader, actual)
                    assert references[reader] == actual, "Timed response changed"
                    active.update(
                        rows=len(response.json()),
                        response_bytes=len(response.content),
                        jena_ms=sum(c["jena_ms"] for c in active["calls"]),
                        backend_ms=sum(c["ms"] for c in active["calls"]),
                        backend_bytes=sum(c["bytes"] for c in active["calls"]),
                    )
                    report["samples"].append(active)
                    print(
                        "DATING_EXPERIMENT",
                        reader,
                        phase,
                        variant,
                        round(active["http_ms"]),
                        flush=True,
                    )
                    active = None
        report["summary"] = {
            reader: {
                variant: {
                    k: statistics.median(
                        s[k]
                        for s in report["samples"]
                        if s["reader"] == reader
                        and s["variant"] == variant
                        and s["phase"] == "timing"
                    )
                    for k in ["http_ms", "jena_ms", "backend_ms", "backend_bytes"]
                }
                for variant in ["baseline", "candidate"]
            }
            for reader in ["public", "audit"]
        }
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error_type"] = type(error).__name__
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        (output / "browser-stop").touch()


if __name__ == "__main__":
    index = sys.argv.index("--cases")
    cases = json.loads(Path(sys.argv[index + 1]).read_text())
    del sys.argv[index : index + 2]
    from functools import partial
    import check_fasnacht_fulltext

    check_fasnacht_fulltext.check_fasnacht_fulltext = partial(exercise, cases=cases)
    runpy.run_path(
        str(Path(__file__).with_name("probe_api_jena.py")), run_name="__main__"
    )
