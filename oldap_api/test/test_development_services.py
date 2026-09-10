"""Music/development transitions preserve writer safety and exact resume state."""

from unittest.mock import Mock, patch

import pytest

import development_services as services
from oldaplib.src.mutation_gate import MutationGateUnavailable


def test_busy_writer_cannot_stop_any_service_or_save_state():
    with (
        patch.object(
            services, "mutation_gate", side_effect=MutationGateUnavailable("busy")
        ),
        patch.object(services, "stop_agent") as stop,
        patch.object(services, "command") as run,
        patch.object(services, "save_state") as save,
    ):
        with pytest.raises(MutationGateUnavailable):
            services.stop_services(Mock(), {})
    stop.assert_not_called()
    run.assert_not_called()
    save.assert_not_called()


def test_backends_must_remain_stopped_before_stores_stop():
    state = {"phase": "backends-stopped", "containers": []}
    with (
        patch.object(services, "job", return_value="unexpected restarted API"),
        patch.object(services, "stop_agent") as stop,
    ):
        with pytest.raises(RuntimeError):
            services.stop_services(Mock(), state)
    stop.assert_not_called()


def test_completed_stop_is_idempotent_but_detects_external_restart():
    state = {"phase": "stopped", "containers": []}
    with (
        patch.object(services, "job", return_value=None),
        patch.object(services, "docker_status", return_value="stopped"),
        patch.object(services, "command") as run,
    ):
        assert services.stop_services(Mock(), state) == state
        run.assert_not_called()
    with patch.object(services, "job", return_value="external restart"):
        with pytest.raises(RuntimeError):
            services.stop_services(Mock(), state)


def test_failed_container_restore_keeps_resume_file(tmp_path):
    path = tmp_path / "development-state.json"
    path.write_text("saved resume state")
    state = {"containers": [{"id": "a" * 64}]}
    with (
        patch.object(services, "LOCAL", tmp_path),
        patch.object(services, "start_agent"),
        patch.object(services, "wait_ready"),
        patch.object(services, "docker_status", return_value="running"),
        patch.object(
            services, "command", side_effect=RuntimeError("missing exact container")
        ),
    ):
        with pytest.raises(RuntimeError):
            services.start_services(Mock(), state)
    assert path.read_text() == "saved resume state"


def test_stopped_desktop_does_not_wait_for_dead_status_rpc():
    with patch.object(
        services,
        "command",
        return_value="/Library/PrivilegedHelperTools/com.docker.vmnetd\n",
    ) as run:
        assert services.docker_status() == "stopped"
        run.assert_called_once_with("/bin/ps", "-axo", "comm=")


def test_container_commands_pin_the_local_desktop_socket():
    with patch.object(services.subprocess, "run", return_value=Mock(stdout="")) as run:
        services.command("docker", "ps")
        argv = run.call_args.args[0]
        assert argv[:2] == ("docker", "--host")
        assert argv[2].endswith("/.docker/run/docker.sock")
        assert argv[3] == "ps"
