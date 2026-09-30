"""Supervise temporary loopback Gunicorn instances and bounded read experiments.

Use the native API interpreter. The existing service on 8000 remains running;
only owned child process groups on 8100 are terminated. No cache flush occurs.
Private logs are retained without writing tokens or response bodies.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

from dotenv import load_dotenv
import requests
import read_performance as baseline
from read_load import content_hash


def port_is_free(port):
    """Refuse to interfere with an existing listener on the experiment port."""
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def stop_owned(process):
    """Drain this experiment's entire process group, escalating only if needed."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=35)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def main():
    """Run matching one/two/four-worker configurations with cold-read checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--workers", type=int, nargs="+", choices=[1, 2, 4], default=[1, 2, 4])
    args = parser.parse_args()
    if not 20 <= args.seconds <= 60:
        parser.error("Use 20..60 seconds per stage")
    args.output = args.output.resolve()
    args.catalog = args.catalog.resolve()
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    load_dotenv(baseline.ROOT / ".env.local", override=True)
    os.environ.update(OLDAP_TS_SERVER=baseline.DB, OLDAP_TS_REPO="oldap",
                      OLDAP_REDIS_URL="redis://localhost:6379/0", APP_ENV="Dev",
                      OLDAP_IIIF_SERVER="http://localhost:8182",
                      OLDAP_UPLOAD_SERVER="http://localhost:8080",
                      OBJC_DISABLE_INITIALIZE_FORK_SAFETY="YES")
    # The orchestrator only queries GraphDB and the experimental read API.
    baseline.install_transport_guard(baseline.Recorder(), api_url="http://localhost:8100")
    before = baseline.fingerprint()
    cases = {c["id"]: c for c in json.loads(args.catalog.read_text())}
    results = []
    try:
        for workers in args.workers:
            if not port_is_free(8100):
                raise RuntimeError("Experiment port 8100 is occupied")
            directory = args.output / f"workers-{workers}"
            directory.mkdir(mode=0o700)
            # Issue a token in the orchestrator using the library's read-only
            # anonymous path. No login has reached any experimental worker.
            from oldaplib.src.connection import Connection
            import oldaplib
            serializer_hash = hashlib.sha256(
                (Path(oldaplib.__file__).parent / "src/helpers/serializer.py").read_bytes()
            ).hexdigest()
            token = Connection(context_name="DEFAULT").token
            command = [sys.executable, "-m", "gunicorn", "oldap_api.wsgi:app",
                       "--bind", "127.0.0.1:8100", "--workers", str(workers),
                       "--worker-class", "gthread", "--threads", "4",
                       "--timeout", "30", "--graceful-timeout", "25",
                       "--config", str(baseline.ROOT / "tools/gunicorn_read_config.py"),
                       "--access-logfile", "-", "--error-logfile", "-"]
            (directory / "command.json").write_text(json.dumps(command, indent=2))
            with (directory / "server.log").open("w") as log:
                process = subprocess.Popen(command, cwd=baseline.ROOT, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    deadline = time.monotonic() + 45
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError("Gunicorn exited during startup")
                        try:
                            response = requests.get("http://localhost:8100/health", timeout=2)
                            if response.status_code == 200:
                                break
                        except requests.RequestException:
                            pass
                        if time.monotonic() > deadline:
                            raise TimeoutError("Gunicorn startup timed out")
                        time.sleep(.2)
                    coverage = defaultdict(set)
                    hashes = {}
                    # Use concurrent clients: a shared listening socket does not
                    # promise fair distribution of serial short connections.
                    def cold_read(key):
                        case = cases[key]
                        r = requests.request(case["method"], "http://localhost:8100"+case["path"],
                                             json=case.get("body"), timeout=(3, 15),
                                             headers={"Authorization": "Bearer "+token,
                                                      "Connection": "close"})
                        r.raise_for_status()
                        if r.headers.get("X-Load-Serializer") != serializer_hash:
                            raise RuntimeError("Worker serializer source differs from orchestrator")
                        return key, r.headers["X-Load-Worker"], content_hash(r.json())

                    keys = ("resource_media", "resource_linked_archive", "datamodel_fasnacht",
                            "summaries_25", "search_sorted", "archive_children",
                            "search_lucene_fields", "hierarchical_list")
                    with ThreadPoolExecutor(max_workers=16) as clients:
                        for _ in range(10):
                            for key in keys:
                                if len(coverage) == workers and all(key in values for values in coverage.values()):
                                    continue
                                for key, pid, digest in clients.map(cold_read, [key] * 16):
                                    if key in hashes and hashes[key] != digest:
                                        raise RuntimeError("Preflight content differs across workers")
                                    hashes[key] = digest
                                    coverage[pid].add(key)
                            (directory / "cold-coverage-progress.json").write_text(json.dumps(
                                {pid: sorted(values) for pid, values in coverage.items()}, indent=2))
                            if len(coverage) == workers and all(len(v) == 8 for v in coverage.values()):
                                break
                        else:
                            raise RuntimeError("Cold-worker coverage incomplete")
                    (directory / "cold-reads.json").write_text(json.dumps(
                        {"workers": {pid: sorted(keys) for pid, keys in coverage.items()},
                         "reference_hashes": hashes,
                         "serializer_sha256": serializer_hash}, indent=2))
                    print(f"{workers} workers: cold bearer reads and warmup verified", flush=True)
                    with (directory / "load.log").open("w") as load_log:
                        subprocess.run([sys.executable, str(baseline.ROOT / "tools/read_load.py"),
                                        "--catalog", str(args.catalog), "--output", str(directory / "load"),
                                        "--api-url", "http://localhost:8100", "--users", "1", "8", "16", "1",
                                        "--seconds", str(args.seconds)], stdout=load_log,
                                       stderr=subprocess.STDOUT, check=True, timeout=4*(args.seconds+30)+60)
                    summary = json.loads((directory / "load/summary.json").read_text())
                    results.append({"workers": workers, **summary})
                    if any(s["aborted"] or s["requests"].get("p95_ms", 0)>2000 for s in summary["stages"]):
                        raise RuntimeError("Load safety threshold reached")
                    print(f"{workers} workers: load complete", flush=True)
                finally:
                    stop_owned(process)
            if not port_is_free(8100):
                raise RuntimeError("Experiment listener did not stop")
    finally:
        after = baseline.fingerprint()
        (args.output / "summary.json").write_text(json.dumps(
            {"configurations": results, "fingerprint_before": before,
             "fingerprint_after": after, "data_unchanged": before == after}, indent=2))
        if before != after:
            raise RuntimeError("Explicit RDF fingerprint changed")


if __name__ == "__main__":
    main()
