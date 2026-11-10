"""Local OLDAP service stop/start for switching between development and music.

No data/volumes are deleted and no stale writer is reset. Frontends remain owned
by their terminals. Other native applications are outside this explicit inventory.
Docker Desktop and ALL its running containers are included by user choice.
"""

import argparse
from contextlib import closing
import fcntl
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import time
from urllib.parse import urlsplit

from dotenv import dotenv_values
import plistlib
from redis import Redis
import requests

from restart_api import load_runtime
from oldaplib.src.mutation_gate import mutation_gate, mark_gate_uncertain
from oldaplib.src.writer_recovery_operator import protected_json

LOCAL = Path.home() / "Library/Application Support/OLDAP/writer-recovery"
LABELS = (
    "org.oldap.api",
    "org.oldap.graphdb",
    "org.oldap.archive-writer",
    "homebrew.mxcl.redis",
)


class MissingResumeContainers(RuntimeError):
    """Saved container identities no longer exist; explicit reconciliation is needed."""


def check_resume_containers(containers):
    """Check exact IDs before starting any container; never substitute by name.

    Only names and short IDs enter the diagnostic, not Docker configuration or
    command stderr, which may contain credentials. Engine failures propagate.
    """
    existing = set(
        command("docker", "ps", "-a", "--no-trunc", "--format", "{{.ID}}").splitlines()
    )
    missing = [item for item in containers if item["id"] not in existing]
    if missing:
        details = ", ".join(
            f"{json.dumps(item.get('name', 'unnamed'), ensure_ascii=True)} ({item['id'][:12]})"
            for item in missing
        )
        raise MissingResumeContainers(
            "Saved Docker containers no longer exist: " + details + ". "
            "Back up and explicitly reconcile development-state.json with the "
            "intended local containers before retrying services-start. "
            "Same-name replacements are not selected automatically. "
            "The resume list was retained; no writer lock was reset."
        )


def command(*argv, timeout=90):
    """Run fixed local commands with bounded waits and no credential output."""
    # Ignore the user's selected remote Docker context for engine operations.
    if argv[0] == "docker" and argv[1] != "desktop":
        argv = (
            "docker",
            "--host",
            f"unix://{Path.home()}/.docker/run/docker.sock",
            *argv[1:],
        )
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=True
    ).stdout


def job(label):
    """Return a loaded launchd job, distinguishing absence from control failure."""
    result = subprocess.run(
        ["/bin/launchctl", "print", f"gui/{os.getuid()}/{label}"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode == 113:
        return None
    result.check_returncode()
    return result.stdout


def stop_agent(label):
    """Disable automatic restart and confirm process exit plus namespace removal."""
    target = f"gui/{os.getuid()}/{label}"
    print(f"Stopping {label}...", flush=True)
    output = job(label)
    command("/bin/launchctl", "disable", target)
    if output is None:
        return
    pid = re.search(r"^\s*pid = (\d+)$", output, re.MULTILINE)
    with closing(select.kqueue()) as queue:
        if pid:
            queue.control(
                [
                    select.kevent(
                        int(pid[1]),
                        filter=select.KQ_FILTER_PROC,
                        flags=select.KQ_EV_ADD,
                        fflags=select.KQ_NOTE_EXIT,
                    )
                ],
                0,
                0,
            )
        command("/bin/launchctl", "bootout", target)
        if pid:
            deadline = time.monotonic() + 70
            while not any(
                event.fflags & select.KQ_NOTE_EXIT
                for event in queue.control(None, 1, 1)
            ):
                if time.monotonic() >= deadline:
                    raise TimeoutError("Native process termination not confirmed.")
    deadline = time.monotonic() + 15
    while job(label) is not None:
        if time.monotonic() >= deadline:
            raise TimeoutError("Native job removal not confirmed.")
        time.sleep(0.1)


def start_agent(label):
    """Enable and bootstrap an existing installed service; never install a new one."""
    print(f"Starting {label}...", flush=True)
    path = Path.home() / "Library/LaunchAgents" / f"{label}.plist"
    if not path.is_file():
        raise ValueError("Required native LaunchAgent is missing.")
    command("/bin/launchctl", "enable", f"gui/{os.getuid()}/{label}")
    if job(label) is None:
        command("/bin/launchctl", "bootstrap", f"gui/{os.getuid()}", str(path))


def docker_status():
    """Avoid Desktop's hanging status RPC once its application/backend has exited.

    Docker's persistent privileged networking helper is not its VM. Native process
    paths under the installed Docker bundle identify the Desktop/VM runtime; when
    present, still require Docker's authoritative engine status.
    """
    processes = command("/bin/ps", "-axo", "comm=")
    if not any(
        line.strip().startswith("/Applications/Docker.app/Contents/")
        for line in processes.splitlines()
    ):
        return "stopped"
    return json.loads(
        command("docker", "desktop", "status", "--format", "json", timeout=10)
    )["Status"]


def save_state(state):
    """Persist the resume list before stopping services, under the local command lock."""
    path = LOCAL / "development-state.json"
    temp = path.with_suffix(".tmp")
    fd = os.open(temp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def wait_ready(check, timeout=60):
    """Bound service readiness; missing dependencies never report successful startup."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise TimeoutError("Service readiness not confirmed.")


def stop_services(client, state):
    """Quiesce writers first, release our normal gate, then stop the two stores."""
    if state.get("phase") == "stopped":
        # Detect external restarts instead of silently claiming a quiet machine.
        if (
            any(job(label) is not None for label in LABELS)
            or docker_status() != "stopped"
        ):
            raise RuntimeError(
                "Services were started outside Make; run services-start before stopping again."
            )
        return state
    if state.get("phase") != "backends-stopped":
        with mutation_gate(client=client, wait_seconds=0):
            # Snapshot all running containers once; exact IDs prevent name reuse.
            if not state:
                status = docker_status()
                if status not in ("running", "stopped"):
                    raise RuntimeError(
                        "Docker Desktop is transitioning; retry when settled."
                    )
                containers = []
                if status == "running":
                    containers = [
                        {"id": item["ID"], "name": item["Names"]}
                        for item in (
                            json.loads(line)
                            for line in command(
                                "docker", "ps", "--no-trunc", "--format", "{{json .}}"
                            ).splitlines()
                        )
                    ]
                state = {"version": 1, "phase": "stopping", "containers": containers}
                save_state(state)
            try:
                ids = [item["id"] for item in state["containers"]]
                if docker_status() == "running" and ids:
                    print(
                        "Stopping Docker containers (allowing up to 60 seconds for shutdown)...",
                        flush=True,
                    )
                    command("docker", "stop", "--time", "60", *ids, timeout=180)
                stop_agent("org.oldap.api")
                stop_agent("org.oldap.graphdb")
            except BaseException:
                mark_gate_uncertain()
                raise
        state["phase"] = "backends-stopped"
        save_state(state)
    # No managed GraphDB writer/database remains; Redis can now stop normally.
    if job("org.oldap.api") is not None or job("org.oldap.graphdb") is not None:
        raise RuntimeError(
            "A backend was externally restarted; storage shutdown refused."
        )
    stop_agent("org.oldap.archive-writer")
    stop_agent("homebrew.mxcl.redis")
    if docker_status() != "stopped":
        print("Stopping Docker Desktop...", flush=True)
        command("docker", "desktop", "stop", "--timeout", "120", timeout=130)
    if docker_status() != "stopped":
        raise RuntimeError("Docker Desktop stop not confirmed.")
    state["phase"] = "stopped"
    save_state(state)
    return state


def start_services(client, state):
    """Start dependencies before API and restore only previously running containers."""
    for label, ready in [
        (
            "homebrew.mxcl.redis",
            lambda: Redis(host="localhost", port=6379, socket_timeout=2).ping(),
        ),
        ("org.oldap.archive-writer", client.ping),
        (
            "org.oldap.graphdb",
            lambda: requests.get(
                "http://localhost:7200/rest/repositories", timeout=2
            ).status_code
            == 200,
        ),
        (
            "org.oldap.api",
            lambda: requests.get(
                "http://localhost:8000/admin/writer-recovery/capabilities", timeout=2
            ).status_code
            == 401,
        ),
    ]:
        start_agent(label)
        wait_ready(ready)
    if docker_status() != "running":
        print("Starting Docker Desktop...", flush=True)
        command("docker", "desktop", "start", "--timeout", "120", timeout=130)
    wait_ready(lambda: docker_status() == "running")
    ids = [item["id"] for item in state.get("containers", [])]
    if ids:
        # Never recreate an absent container or silently select a reused name.
        check_resume_containers(state["containers"])
        command("docker", "inspect", "--format", "{{json .State}}", *ids)
        command("docker", "start", *ids, timeout=180)
        if not all(
            item["Running"]
            for item in [
                json.loads(line)
                for line in command(
                    "docker", "inspect", "--format", "{{json .State}}", *ids
                ).splitlines()
            ]
        ):
            raise RuntimeError("Container startup not confirmed.")
    (LOCAL / "development-state.json").unlink(missing_ok=True)


JENA_LABELS = (
    "homebrew.mxcl.redis", "org.oldap.archive-writer", "org.oldap.jena-redis",
    "org.oldap.jena-identity", "org.oldap.jena", "org.oldap.api",
)


CONSOLE_LABEL = "org.oldap.jena-console"


def jena_labels():
    """Include the optional local console only after its LaunchAgent is installed."""
    console = Path.home() / "Library/LaunchAgents" / (CONSOLE_LABEL + ".plist")
    return (*JENA_LABELS, CONSOLE_LABEL) if console.is_file() else JENA_LABELS


def jena_runtime(environment):
    """Validate native Jena ownership before controlling installed LaunchAgents.

    Both Python services must use this exact environment and checkout. Runtime
    state is separate from the legacy GraphDB writer-recovery inventory.
    """
    settings = dotenv_values(environment)
    if settings.get("OLDAP_BACKEND") != "jena":
        raise ValueError("Expected explicit Jena backend")
    root = Path(__file__).resolve().parent
    for label, role in (("org.oldap.api", "api"), ("org.oldap.jena-identity", "identity")):
        path = Path.home() / "Library/LaunchAgents" / (label + ".plist")
        args = plistlib.loads(path.read_bytes())["ProgramArguments"]
        expected = [str(root / ".venv/bin/python"), str(root / "native_service.py"),
                    role, "--environment", str(environment.resolve())]
        if args != expected:
            raise ValueError("LaunchAgent does not match this checkout/environment: " + label)
    if (settings.get("OLDAP_JENA_URL") != "http://127.0.0.1:3031/tx"
            or settings.get("OLDAP_API_PORT", "8000") != "8000"):
        raise ValueError("Native controller requires its fixed loopback endpoints")
    for key, database in (("OLDAP_REDIS_URL", "/0"), ("OLDAP_STAGING_LOCK_REDIS_URL", "/1")):
        address = urlsplit(settings[key])
        if (address.scheme, address.hostname, address.port, address.path) != ("redis", "127.0.0.1", 6381, database):
            raise ValueError("Native controller requires its dedicated local Redis databases")
    return settings


def jena_stop(state):
    """Drain local consumers before closing Jena and Redis; retain resumable state.

    Stop is deliberate maintenance: finish interactive uploads/imports first.
    No stale transaction or writer ownership is reset. Jena's SIGTERM handler
    drains requests, aborts any remaining transaction and closes TDB cleanly.
    """
    if state.get("phase") == "stopped":
        if any(job(label) is not None for label in jena_labels()) or docker_status() != "stopped":
            raise RuntimeError("Services were externally started; run services-start before stopping again")
        return
    if not state:
        status = docker_status()
        if status not in ("running", "stopped"):
            raise RuntimeError("Docker Desktop is transitioning")
        containers = []
        if status == "running":
            containers = [{"id": row["ID"], "name": row["Names"]} for row in
                          map(json.loads, command("docker", "ps", "--no-trunc", "--format", "{{json .}}").splitlines())]
        state = {"version": 2, "phase": "stopping", "containers": containers,
                 "docker_running": status == "running"}
        save_state(state)
    ids = [item["id"] for item in state["containers"]]
    if ids and docker_status() == "running":
        command("docker", "stop", "--time", "120", *ids, timeout=300)
    # Close console/API ingress first, database before verifier, and stores last. Never force-kill TDB.
    for label in reversed(jena_labels()):
        stop_agent(label)
    if docker_status() != "stopped":
        command("docker", "desktop", "stop", "--timeout", "120", timeout=130)
    if docker_status() != "stopped" or any(job(label) for label in jena_labels()):
        raise RuntimeError("Local stop not confirmed")
    state["phase"] = "stopped"
    save_state(state)


def jena_start(settings, state):
    """Start stores, independent identity, Jena and API in dependency order."""
    for label in jena_labels():
        start_agent(label)
        if label == CONSOLE_LABEL:
            wait_ready(lambda: requests.get("http://127.0.0.1:3030/_ready", timeout=2).status_code == 200)
        elif label == "org.oldap.jena-redis":
            with Redis.from_url(settings["OLDAP_STAGING_LOCK_REDIS_URL"], socket_timeout=2) as client:
                wait_ready(client.ping)
        elif label in ("org.oldap.jena-identity", "org.oldap.jena", "org.oldap.api"):
            endpoint = {"org.oldap.jena-identity": "http://127.0.0.1:8001/_ready",
                        "org.oldap.jena": "http://127.0.0.1:3031/health",
                        "org.oldap.api": "http://127.0.0.1:8000/status"}[label]
            wait_ready(lambda: requests.get(endpoint, timeout=2).status_code == 200)
    if state.get("docker_running", True):
        if docker_status() != "running":
            command("docker", "desktop", "start", "--timeout", "120", timeout=130)
        wait_ready(lambda: docker_status() == "running")
        if state.get("containers"):
            check_resume_containers(state["containers"])
            ids = [item["id"] for item in state["containers"]]
            command("docker", "start", *ids, timeout=180)
            rows = command("docker", "inspect", "--format", "{{json .State}}", *ids)
            if not all(json.loads(row)["Running"] for row in rows.splitlines()):
                raise RuntimeError("Container startup not confirmed")
    (LOCAL / "development-state.json").unlink(missing_ok=True)


def control_jena(args):
    """Serialize local commands; keep failed resume state for explicit recovery."""
    global LOCAL
    settings = jena_runtime(args.environment)
    LOCAL = Path.home() / "Library/Application Support/OLDAP/local-jena"
    LOCAL.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (LOCAL / "development-control.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = LOCAL / "development-state.json"
        state = protected_json(str(path)) if path.exists() else {}
        if state and (state.get("version") != 2 or state.get("phase") not in ("stopping", "stopped")
                      or any(not re.fullmatch(r"[a-f0-9]{64}", item["id"]) for item in state["containers"])):
            raise ValueError("Invalid Jena resume state")
        if args.action == "restart":
            if state:
                raise RuntimeError("Complete services-start before restarting the API")
            stop_agent("org.oldap.api")
            start_agent("org.oldap.api")
            wait_ready(lambda: requests.get("http://127.0.0.1:8000/status", timeout=2).status_code == 200)
        elif args.action == "stop":
            jena_stop(state)
        elif args.action == "start":
            jena_start(settings, state)
        for label in jena_labels():
            print(f'{label}: {"loaded" if job(label) is not None else "stopped"}')
        print("Docker Desktop:", docker_status())
        print("Frontends: use Ctrl+C / npm run dev in their terminals.")


def main():
    """Serialize Make invocations and leave a durable resume list on partial failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["stop", "start", "status"])
    parser.add_argument("--environment", type=Path, default=Path(".env.local"))
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.exit(1, "These targets require the native macOS installation.\n")
    try:
        if dotenv_values(args.environment).get("OLDAP_BACKEND") == "jena":
            control_jena(args)
            return
        _, _, url = load_runtime(args.environment)
        with open(LOCAL / "development-control.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            path = LOCAL / "development-state.json"
            state = protected_json(str(path)) if path.exists() else {}
            if state and (
                state.get("version") != 1
                or state.get("phase") not in ("stopping", "backends-stopped", "stopped")
                or any(
                    not re.fullmatch(r"[a-f0-9]{64}", item["id"])
                    for item in state["containers"]
                )
            ):
                raise ValueError(
                    "Invalid saved service state; inspect it before retrying."
                )
            with Redis.from_url(
                url, decode_responses=True, socket_connect_timeout=5, socket_timeout=10
            ) as client:
                if args.action == "stop":
                    stop_services(client, state)
                elif args.action == "start":
                    start_services(client, state)
            for label in LABELS:
                print(f'{label}: {"loaded" if job(label) is not None else "stopped"}')
            print("Docker Desktop:", docker_status())
            print("Frontends: use Ctrl+C / npm run dev in their terminals.")
    except MissingResumeContainers as exc:
        parser.exit(1, str(exc) + "\n")
    except Exception:
        parser.exit(
            1,
            "Service operation not confirmed. Inspect local service state/logs; retry services-start to restore dependencies. No retained writer lock was reset.\n",
        )


if __name__ == "__main__":
    main()
