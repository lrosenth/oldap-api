"""Profile captured archive-page searches against a disposable real-data API.

Run with the normal probe_api_jena CLI, --browser-preview --fulltext-preview,
--fasnacht-export and --cases JSON. Cases contain only public search paths/bodies.
Production is never instrumented. Unprofiled wall-time samples and separate CPU
profiles distinguish Jena dispatch/authentication, transport and Python overhead.
The owned preview remains available for an end-to-end local browser measurement.
"""

import cProfile
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path
import pstats
import runpy
import statistics
import sys
import time
from unittest.mock import patch

import requests
from flask import Flask, request


def exercise(call, con, base, output, public, audit, *, cases):
    """Replay exact public-reader payloads; instrumentation never changes queries.

    Jena dispatch includes parsing, query execution and result serialization.
    Python remainder excludes backend HTTP waits; decode/date spans are nested
    diagnostics, not additional independent costs. CPU profiles are not used as
    latency measurements. Background requests are excluded by a request context.
    """
    from oldaplib.src.jena_connection import JenaConnection
    from oldap_api.views import instance_views

    active = ContextVar("archive_profile", default=None)
    target = None
    originals = dict(
        http=requests.sessions.Session.request,
        dispatch=Flask.full_dispatch_request,
        decode=JenaConnection._decode,
        dating=instance_views._expand_search_dating,
    )
    samples, profiles = [], {}

    def http(session, method, url, **kwargs):
        current = active.get()
        if current is None or not url.startswith(con._jena.url + "/"):
            return originals["http"](session, method, url, **kwargs)
        kwargs["headers"] = {**kwargs.get("headers", {}), "X-Probe-Timing": "yes"}
        body = kwargs.get("data", "")
        if isinstance(body, bytes):
            body = body.decode()
        key = hashlib.sha256(body.encode()).hexdigest()[:16]
        (output / ("request-" + key + ".txt")).write_text(body)
        start = time.perf_counter()
        response = originals["http"](session, method, url, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        current["calls"].append(
            dict(
                query=key,
                operation=url[len(con._jena.url) + 1 :].split("/")[0],
                ms=elapsed,
                authentication_ms=int(response.headers["X-Probe-Authentication-Nanos"])
                / 1e6,
                dispatch_ms=int(response.headers["X-Probe-Dispatch-Nanos"]) / 1e6,
                bytes=len(response.content),
            )
        )
        return response

    def dispatch(app):
        if target is None or request.path != target["path"]:
            return originals["dispatch"](app)
        token = active.set(target)
        profiler = cProfile.Profile() if target["phase"] == "profile" else None
        start = time.perf_counter()
        if profiler:
            profiler.enable()
        try:
            return originals["dispatch"](app)
        finally:
            target["api_ms"] = (time.perf_counter() - start) * 1000
            if profiler:
                profiler.disable()
                profiler.dump_stats(str(output / (str(target["case"]) + ".prof")))
                stats = pstats.Stats(profiler)
                rows = [
                    dict(
                        function=f"{Path(k[0]).name}:{k[1]}:{k[2]}",
                        calls=v[1],
                        self_ms=v[2] * 1000,
                        cumulative_ms=v[3] * 1000,
                    )
                    for k, v in stats.stats.items()
                ]
                profiles[str(target["case"])] = dict(
                    self=sorted(rows, key=lambda x: x["self_ms"], reverse=True)[:25],
                    cumulative=sorted(
                        rows, key=lambda x: x["cumulative_ms"], reverse=True
                    )[:25],
                )
            active.reset(token)

    def timed(name):
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return originals[name](*args, **kwargs)
            finally:
                current = active.get()
                if current is not None:
                    current[name + "_ms"] = (
                        current.get(name + "_ms", 0)
                        + (time.perf_counter() - start) * 1000
                    )

        return wrapper

    with patch.object(requests.sessions.Session, "request", http), patch.object(
        Flask, "full_dispatch_request", dispatch
    ), patch.object(
        JenaConnection, "_decode", staticmethod(timed("decode"))
    ), patch.object(
        instance_views, "_expand_search_dating", timed("dating")
    ):
        for phase in ["warmup"] + ["timing"] * 4 + ["profile"]:
            for i, case in enumerate(cases):
                target = dict(case=i, path=case["path"], phase=phase, calls=[])
                start = time.perf_counter()
                response = requests.post(
                    base + case["path"],
                    json=case["body"],
                    headers={**public, "Accept": "application/json; dating=structured"},
                    timeout=60,
                )
                target["http_ms"] = (time.perf_counter() - start) * 1000
                response.raise_for_status()
                payload = response.json()
                target.update(
                    rows=len(payload) if isinstance(payload, list) else None,
                    response_bytes=len(response.content),
                )
                for key, field in [
                    ("backend_ms", "ms"),
                    ("jena_ms", "dispatch_ms"),
                    ("authentication_ms", "authentication_ms"),
                ]:
                    target[key] = sum(x[field] for x in target["calls"])
                target["python_ms"] = target["api_ms"] - target["backend_ms"]
                target["transport_ms"] = (
                    target["backend_ms"]
                    - target["jena_ms"]
                    - target["authentication_ms"]
                )
                samples.append(target)
                print(
                    "ARCHIVE_PROFILE",
                    i,
                    phase,
                    round(target["http_ms"]),
                    target["rows"],
                    flush=True,
                )
                target = None
    metrics = [
        "http_ms",
        "api_ms",
        "backend_ms",
        "jena_ms",
        "authentication_ms",
        "python_ms",
        "transport_ms",
        "decode_ms",
        "dating_ms",
    ]
    summary = {
        str(i): {
            k: statistics.median(
                s.get(k, 0)
                for s in samples
                if s["case"] == i and s["phase"] == "timing"
            )
            for k in metrics
        }
        for i in range(len(cases))
    }
    report = dict(
        cases=cases,
        samples=samples,
        summary=summary,
        profiles=profiles,
        scope="Owned fixture, sequential unprofiled samples; separate cProfile runs; no production instrumentation",
    )
    (output / "archive-page-profile.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )


if __name__ == "__main__":
    index = sys.argv.index("--cases")
    cases = json.loads(Path(sys.argv[index + 1]).read_text())
    del sys.argv[index : index + 2]
    assert cases and all(
        c["path"].startswith("/data/search/") and isinstance(c["body"], dict)
        for c in cases
    )
    from functools import partial
    import check_fasnacht_fulltext

    check_fasnacht_fulltext.check_fasnacht_fulltext = partial(exercise, cases=cases)
    runpy.run_path(
        str(Path(__file__).with_name("probe_api_jena.py")), run_name="__main__"
    )
