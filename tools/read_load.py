"""Bounded, read-only live HTTP workload; no app construction or cache clearing.

Replay an existing read_performance catalog with independent anonymous sessions.
Closed-loop users execute fixed reference workflows and think for 0.5–1.5 s.
Artifacts contain timings, hashes and process metrics, never tokens or payloads.
Run with the native API Python; macOS lsof/ps are used for process sampling.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import random
import statistics
import subprocess
import threading
import time
from urllib.parse import urlsplit

import requests
import read_performance as baseline

WORKFLOWS = {
    "search_metadata": ("search_sorted", "summaries_25"),
    "open_resource": ("resource_media",),
    "archive_navigation": ("archive_children", "resource_linked_archive"),
    "fulltext": ("search_lucene_fields",),
    "model": ("datamodel_fasnacht",),
    "list": ("hierarchical_list",),
}
CYCLE = ("search_metadata", "open_resource", "search_metadata",
         "archive_navigation", "open_resource", "fulltext", "search_metadata",
         "open_resource", "archive_navigation", "model",
         "search_metadata", "open_resource", "search_metadata",
         "archive_navigation", "open_resource", "fulltext", "search_metadata",
         "open_resource", "archive_navigation", "list")


def content_hash(value):
    """Ignore unordered RDF arrays and independently issued media capabilities."""
    def normalize(item):
        if isinstance(item, dict):
            return {k: bool(v) if k == "capability" else normalize(v)
                    for k, v in item.items()}
        if isinstance(item, list):
            return sorted((normalize(v) for v in item),
                          key=lambda v: json.dumps(v, sort_keys=True))
        return item
    return baseline.digest(normalize(value))


def stats(values):
    """Return nearest-rank tail latency with an explicit sample count."""
    values = sorted(values)
    if not values:
        return {"n": 0}
    return {"n": len(values), "p50_ms": statistics.median(values),
            "p95_ms": values[math.ceil(.95 * len(values)) - 1],
            "max_ms": values[-1]}


def cpu_seconds(value):
    """Parse macOS ps accumulated CPU time, including optional day prefix."""
    days, clock = value.split("-", 1) if "-" in value else ("0", value)
    total = 0.0
    for part in clock.split(":"):
        total = total * 60 + float(part)
    return int(days) * 86400 + total


def process_snapshot(pids):
    """Read cumulative process CPU and RSS without attaching a profiler."""
    result = {}
    for name, pid in pids.items():
        line = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "time=,rss="], text=True).strip()
        cpu, rss = line.split()
        result[name] = {"cpu_seconds": cpu_seconds(cpu), "rss_mib": int(rss)/1024}
    return result


def process_ids(api_url=baseline.API):
    """Resolve all API listeners (Gunicorn master/workers share one socket)."""
    result = {"load_client": os.getpid()}
    port = urlsplit(api_url).port
    services = [("api", port), ("graphdb", 7200), ("redis", 6379)]
    if port != 8000:
        services.append(("existing_api", 8000))
    for name, service_port in services:
        pids = sorted(set(subprocess.check_output(
            ["lsof", "-t", f"-iTCP:{service_port}", "-sTCP:LISTEN"], text=True).split()), key=int)
        if not pids or (name != "api" and len(pids) != 1):
            raise RuntimeError(f"Unexpected listener count for {name}")
        for pid in pids:
            result[f"api_{pid}" if name == "api" else name] = int(pid)
    return result


def run_stage(users, seconds, cases, sessions, references, pids, *, snapshot=None):
    """Run one drained stage, aborting new requests on errors or >5 s latency.

    Users have independent Sessions; results are merged only after futures finish.
    A stop prevents new work but allows already submitted reads to finish.
    The optional snapshot callable supplies Linux/Docker metrics for VM runs;
    the default retains local macOS process sampling.
    """
    snapshot = snapshot or process_snapshot
    stop = threading.Event()
    start = time.perf_counter()
    deadline = start + seconds
    initial = snapshot(pids)
    samples = []

    def user(index):
        rng = random.Random(4200 + index)
        rows, flows = [], []
        counter = index
        stop.wait(index * .05)
        while time.perf_counter() < deadline and not stop.is_set():
            workflow = CYCLE[counter % len(CYCLE)]
            began = time.perf_counter()
            complete = True
            for case_id in WORKFLOWS[workflow]:
                if stop.is_set():
                    complete = False
                    break
                case = cases[case_id]
                request_start = time.perf_counter()
                status, size, error, same = 0, 0, None, False
                worker_pid = None
                try:
                    response = sessions[index].request(
                        case["method"], baseline.API + case["path"],
                        json=case.get("body"), timeout=(3, 10))
                    status, size = response.status_code, len(response.content)
                    worker_pid = response.headers.get("X-Load-Worker")
                    elapsed = (time.perf_counter() - request_start) * 1000
                    same = status == 200 and content_hash(response.json()) == references[case_id]
                except Exception as exc:
                    elapsed = (time.perf_counter() - request_start) * 1000
                    error = type(exc).__name__
                rows.append({"user": index, "case": case_id, "workflow": workflow,
                             "start_s": request_start-start, "ms": elapsed,
                             "status": status, "bytes": size, "content_equal": same,
                             "error": error, "worker_pid": worker_pid})
                if not same or elapsed > 5000:
                    stop.set()
                    complete = False
                    break
            flows.append({"workflow": workflow, "complete": complete,
                          "ms": (time.perf_counter()-began)*1000})
            counter += 1
            stop.wait(rng.uniform(.5, 1.5))
        return rows, flows

    with ThreadPoolExecutor(max_workers=users) as pool:
        futures = [pool.submit(user, index) for index in range(users)]
        while not all(f.done() for f in futures):
            samples.append({"elapsed_s": time.perf_counter()-start,
                            "processes": snapshot(pids)})
            time.sleep(1)
        results = [f.result() for f in futures]
    elapsed = time.perf_counter()-start
    final = snapshot(pids)
    rows = [row for result, _ in results for row in result]
    flows = [row for _, result in results for row in result]
    cpu = {name: 100*(final[name]["cpu_seconds"]-initial[name]["cpu_seconds"])/elapsed
           for name in pids}
    cpu["api_total"] = sum(value for name, value in cpu.items() if name.startswith("api_"))
    summary = {"users": users, "elapsed_s": elapsed, "aborted": stop.is_set(),
               "requests_per_second": len(rows)/elapsed,
               "completed_workflows_per_second": sum(f["complete"] for f in flows)/elapsed,
               "errors": sum(not r["content_equal"] for r in rows),
               "requests": stats([r["ms"] for r in rows]),
               "workflows": stats([r["ms"] for r in flows if r["complete"]]),
               "cpu_percent_one_core": cpu,
               "by_case": {key: stats([r["ms"] for r in rows if r["case"] == key])
                           for key in references},
               "by_workflow": {key: stats([r["ms"] for r in flows
                                           if r["workflow"] == key and r["complete"]])
                               for key in WORKFLOWS}}
    return {"summary": summary, "requests": rows, "workflows": flows, "samples": samples}


def main():
    """Preflight fixed reads, run bounded ramp/recovery, verify RDF fingerprint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--api-url", default=baseline.API)
    parser.add_argument("--users", type=int, nargs="+", default=[1, 2, 4, 8, 16, 1])
    args = parser.parse_args()
    target = urlsplit(args.api_url)
    if (target.scheme != "http" or target.hostname != "localhost" or
            target.port is None or target.path or target.query or target.fragment or
            target.username or target.password):
        parser.error("Use http://localhost:PORT without credentials or path")
    if not args.users or any(n < 1 or n > 16 for n in args.users):
        parser.error("Each stage requires 1..16 users")
    baseline.API = args.api_url
    if not 20 <= args.seconds <= 90:
        parser.error("Stage duration must be 20..90 seconds")
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    # Recorder remains inactive: no non-thread-safe request profiling is installed.
    baseline.install_transport_guard(baseline.Recorder(), api_url=args.api_url)
    cases = {case["id"]: case for case in json.loads(args.catalog.read_text())}
    needed = {key for flow in WORKFLOWS.values() for key in flow}
    cases = {key: cases[key] for key in needed}
    before = baseline.fingerprint()
    pids = process_ids(args.api_url)
    inventory = baseline.inventory()
    inventory.update(fingerprint=before, pids=pids,
                     started_utc=datetime.now(timezone.utc).isoformat(),
                     api_url=args.api_url, user_stages=args.users,
                     stage_seconds=args.seconds, think_seconds=[.5, 1.5],
                     cycle=CYCLE, workflows=WORKFLOWS)
    (args.output/"inventory.json").write_text(json.dumps(inventory, indent=2))
    sessions, stages = [], []
    try:
        for _ in range(max(args.users)):
            session = requests.Session()
            response = session.post(baseline.API + "/admin/auth/unknown", json={})
            response.raise_for_status()
            session.headers["Authorization"] = "Bearer " + response.json()["accessToken"]
            sessions.append(session)
        references = {}
        for key, case in cases.items():
            response = sessions[0].request(case["method"], baseline.API+case["path"],
                                           json=case.get("body"))
            response.raise_for_status()
            references[key] = content_hash(response.json())
        for index, users in enumerate(args.users):
            stage = run_stage(users, args.seconds, cases, sessions, references, pids)
            stage["summary"]["stage"] = index
            stages.append(stage["summary"])
            (args.output/f"stage-{index}.json").write_text(json.dumps(stage, indent=2))
            print(json.dumps(stage["summary"]), flush=True)
            if stage["summary"]["aborted"] or stage["summary"]["requests"].get("p95_ms", 0) > 2000:
                break
            time.sleep(3)
    finally:
        for session in sessions:
            session.close()
        after = baseline.fingerprint()
        (args.output/"summary.json").write_text(json.dumps(
            {"stages": stages, "fingerprint_before": before, "fingerprint_after": after,
             "data_unchanged": before == after}, indent=2))
        if after != before:
            raise RuntimeError("Explicit named-graph fingerprint changed")


if __name__ == "__main__":
    main()
