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


def main():
    """Serialize Make invocations and leave a durable resume list on partial failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["stop", "start", "status"])
    parser.add_argument("--environment", type=Path, default=Path(".env.local"))
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.exit(1, "These targets require the native macOS installation.\n")
    try:
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
    except Exception:
        parser.exit(
            1,
            "Service operation not confirmed. Inspect local service state/logs; retry services-start to restore dependencies. No retained writer lock was reset.\n",
        )


if __name__ == "__main__":
    main()
