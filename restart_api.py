"""Restart the reviewed local launchd API while holding the normal writer gate.

Invoked by ``make restart``. This is not recovery: an occupied/uncertain gate is
refused. GraphDB, Redis and the frontends are never restarted by this command.
"""

import argparse
from contextlib import closing
from pathlib import Path
import plistlib
import select
import subprocess
import sys
import time
from urllib.parse import urlsplit

from dotenv import dotenv_values
from redis import Redis
import requests

from oldaplib.src.mutation_gate import mutation_gate, mark_gate_uncertain
from oldaplib.src.writer_recovery_macos import LaunchdDomain
from oldaplib.src.writer_recovery_operator import protected_json, inventory_digest


def restart(domain: LaunchdDomain, client: Redis, service: dict) -> None:
    """Stop/start one supervised API, refusing concurrent writes atomically.

    Confirm the old process exit and launchd job removal before starting a new
    instance. Retain ownership if service control fails or its outcome is unknown;
    a delayed control command must never overtake a newly admitted writer.
    """
    with mutation_gate(client=client, wait_seconds=0):
        before = domain.identity(service)
        with closing(select.kqueue()) as queue:
            queue.control(
                [
                    select.kevent(
                        before["pid"],
                        filter=select.KQ_FILTER_PROC,
                        flags=select.KQ_EV_ADD,
                        fflags=select.KQ_NOTE_EXIT,
                    )
                ],
                0,
                0,
            )
            if domain.identity(service) != before:
                raise RuntimeError(
                    "API changed before restart; retry after inspection."
                )
            try:
                domain.run("bootout", f"{domain.target}/{service['label']}")
                deadline = time.monotonic() + 70
                while True:
                    events = queue.control(None, 1, 1)
                    if any(event.fflags & select.KQ_NOTE_EXIT for event in events):
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError("API process exit was not confirmed.")
                deadline = time.monotonic() + 15
                while True:
                    result = subprocess.run(
                        [
                            "/bin/launchctl",
                            "print",
                            f"{domain.target}/{service['label']}",
                        ],
                        capture_output=True,
                        timeout=10,
                    )
                    if result.returncode == 113:
                        break
                    if result.returncode != 0 or time.monotonic() >= deadline:
                        raise RuntimeError("API service removal was not confirmed.")
                    time.sleep(0.1)
                domain.run("bootstrap", domain.target, service["plist"])
                deadline = time.monotonic() + 30
                while True:
                    try:
                        response = requests.get(
                            "http://localhost:8000/admin/writer-recovery/capabilities",
                            timeout=2,
                        )
                        if (
                            response.status_code == 401
                            and domain.identity(service) != before
                        ):
                            break
                    except (
                        requests.RequestException,
                        ValueError,
                        subprocess.CalledProcessError,
                    ):
                        pass
                    if time.monotonic() >= deadline:
                        raise TimeoutError("API startup was not confirmed.")
                    time.sleep(0.2)
            except BaseException:
                mark_gate_uncertain()
                raise


def load_runtime(environment: Path):
    """Validate the local inventory, API environment and shared writer-store address."""
    config = protected_json(
        str(
            Path.home()
            / "Library/Application Support/OLDAP/writer-recovery/operator.json"
        )
    )
    env = dotenv_values(environment)
    if env.get("OLDAP_WRITER_RECOVERY_INVENTORY_SHA256") != inventory_digest(config):
        raise ValueError("Environment does not match the reviewed native inventory.")
    service = next(
        item for item in config["nativeServices"] if item["label"] == "org.oldap.api"
    )
    domain = LaunchdDomain(config)
    with open(service["plist"], "rb") as stream:
        argv = plistlib.load(stream)["ProgramArguments"]
    if Path(argv[argv.index("--environment") + 1]).resolve() != environment.resolve():
        raise ValueError("Selected environment is not used by the managed API.")
    url = env["OLDAP_STAGING_LOCK_REDIS_URL"]

    def store_address(value):
        parsed = urlsplit(value)
        return (
            parsed.scheme,
            parsed.hostname,
            parsed.port,
            parsed.path,
            parsed.query,
        )

    if store_address(url) != store_address(config["operatorRedisUrl"]):
        raise ValueError("Writer store differs from the managed coordination domain.")
    return domain, service, url


def main() -> None:
    """Load private local settings without printing credentials or process output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", type=Path, default=Path(".env.local"))
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.exit(1, "make restart requires the native macOS launchd installation.\n")
    try:
        domain, service, url = load_runtime(args.environment)
        with Redis.from_url(
            url, decode_responses=True, socket_connect_timeout=5, socket_timeout=10
        ) as client:
            restart(domain, client, service)
    except Exception:
        parser.exit(
            1,
            "API restart not confirmed. Check active writes/recovery, local configuration and service logs. No existing writer lock was reset.\n",
        )
    print("API restarted at http://localhost:8000; writer gate released.")


if __name__ == "__main__":
    main()
