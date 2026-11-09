"""Compare request-scoped schema discovery and broad metadata ACL placement.

Uses probe_api_jena's CLI plus --cases, --browser-preview and --fulltext-preview.
Baseline disables schema reuse and restores the previous role cross-product; scoped changes
only schema reuse; candidate also joins the extracted grant role directly to current membership. Exact public/audit HTTP responses and native ACL/date
fixtures must match before timing. No production configuration is read or changed.
"""

from contextlib import nullcontext, ExitStack
import json
from pathlib import Path
import runpy
import statistics
import sys
import time
from unittest.mock import patch

import requests
from flask import Flask

# Exact generated joins keep the comparison independent of new runtime choices.
_LEGACY_ACL_JOIN = "    GRAPH oldap:admin {{\n        {con.userIri.toRdf} oldap:hasRole ?role .\n        ?DataPermission oldap:permissionValue ?permval .\n        FILTER(?permval >= {DataPermission.DATA_VIEW.numeric.toRdf})\n    }}\n    GRAPH {graph}:data {{\n        ?searchGrant rdf:reifies ?accessTriple ; oldap:hasDataPermission ?DataPermission .\n        FILTER(isTRIPLE(?accessTriple) && PREDICATE(?accessTriple) = oldap:attachedToRole)\n        BIND(SUBJECT(?accessTriple) AS ?res)\n        BIND(OBJECT(?accessTriple) AS ?grantedRole)\n        FILTER(?grantedRole = ?role)\n        ?res oldap:attachedToRole ?role ; rdf:type {resclass_var} .\n    }}"
_CANDIDATE_ACL_JOIN = "    GRAPH {graph}:data {{\n        ?searchGrant rdf:reifies ?accessTriple ; oldap:hasDataPermission ?DataPermission .\n        FILTER(isTRIPLE(?accessTriple) && PREDICATE(?accessTriple) = oldap:attachedToRole)\n        BIND(SUBJECT(?accessTriple) AS ?res)\n        BIND(OBJECT(?accessTriple) AS ?role)\n    }}\n    GRAPH oldap:admin {{\n        {con.userIri.toRdf} oldap:hasRole ?role .\n        ?DataPermission oldap:permissionValue ?permval .\n        FILTER(?permval >= {DataPermission.DATA_VIEW.numeric.toRdf})\n    }}\n    GRAPH {graph}:data {{\n        ?res oldap:attachedToRole ?role ; rdf:type {resclass_var} .\n    }}"


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

    from oldaplib.src.jena_connection import JenaConnection
    from oldaplib.src.enums.datapermissions import DataPermission

    original_query = JenaConnection.query
    original_http = requests.sessions.Session.request
    active = None
    report = {"status": "running", "checks": [], "samples": [], "differences": []}
    report_path = output / "metadata-experiment.json"

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
        def previous_query(connection, query, *args, **kwargs):
            # Restore the previous role cross-product, leaving all ACL rules intact.
            substitutions = dict(
                graph="fasnacht",
                con=connection,
                DataPermission=DataPermission,
                resclass_var="?searchResclass",
            )
            new_join = _CANDIDATE_ACL_JOIN.format(**substitutions)
            old_join = _LEGACY_ACL_JOIN.format(**substitutions)
            if "{ SELECT DISTINCT ?res ?searchResclass WHERE {" in query:
                assert new_join in query, "Comparison did not recognize broad ACL join"
                report["baseline_query_rewrites"] = (
                    report.get("baseline_query_rewrites", 0) + 1
                )
                query = query.replace(new_join, old_join, 1)
            return original_query(connection, query, *args, **kwargs)

        with ExitStack() as control:
            if variant == "baseline":
                control.enter_context(
                    patch.object(
                        JenaConnection,
                        "_resource_schema_scope",
                        lambda self: nullcontext(),
                    )
                )
            if variant != "candidate":
                control.enter_context(
                    patch.object(JenaConnection, "query", previous_query)
                )
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

        # Counts and nonzero offsets must keep the same matches and order.
        for reader, headers in [("public", public), ("audit", audit)]:
            for body in [
                dict(cases[7]["body"], limit=100, offset=0),
                dict(cases[7]["body"], limit=100, offset=100),
                dict(cases[7]["body"], countOnly=True),
            ]:
                case = {"path": cases[7]["path"], "body": body}
                before = read(case, headers, "baseline").json()
                after = read(case, headers, "candidate").json()
                assert canonical(before) == canonical(after), (reader, body)
                report["checks"].append(f"{reader}: paging/count response equal")

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
                search_case = {
                    "path": "/data/search/fasnacht/class/fasnacht:CarnivalEvent",
                    "body": {"limit": 5000, "includeProperties": ["schema:name"]},
                }
                old_rows = read(search_case, public, "baseline").json()
                new_rows = read(search_case, public, "candidate").json()
                assert canonical(old_rows) == canonical(new_rows)
                actual = {row["iri"] for row in new_rows if row["iri"].startswith(ns)}
                assert actual == wanted - {ns + "creator"}, actual
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
                for index, case in enumerate(cases):
                    sequence = [
                        ("warmup", v) for v in ["baseline", "scoped", "candidate"]
                    ]
                    sequence += [
                        ("timing", v)
                        for v in [
                            "baseline",
                            "scoped",
                            "candidate",
                            "candidate",
                            "scoped",
                            "baseline",
                        ]
                        * 2
                    ]
                    for phase, variant in sequence:
                        active = {
                            "reader": reader,
                            "case": index,
                            "phase": phase,
                            "variant": variant,
                            "calls": [],
                        }
                        start = time.perf_counter()
                        response = read(case, headers, variant)
                        active["http_ms"] = (time.perf_counter() - start) * 1000
                        actual = canonical(response.json())
                        references.setdefault((reader, index), actual)
                        assert (
                            references[(reader, index)] == actual
                        ), "Timed response changed"
                        active.update(
                            rows=len(response.json()),
                            jena_ms=sum(c["jena_ms"] for c in active["calls"]),
                            backend_calls=len(active["calls"]),
                        )
                        report["samples"].append(active)
                        active = None
                    print("METADATA_EXPERIMENT", reader, index, "passed", flush=True)
        report["summary"] = {
            reader: {
                str(index): {
                    variant: {
                        key: statistics.median(
                            sample[key]
                            for sample in report["samples"]
                            if sample["reader"] == reader
                            and sample["case"] == index
                            and sample["variant"] == variant
                            and sample["phase"] == "timing"
                        )
                        for key in ["http_ms", "jena_ms", "backend_calls"]
                    }
                    for variant in ["baseline", "scoped", "candidate"]
                }
                for index in range(len(cases))
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
