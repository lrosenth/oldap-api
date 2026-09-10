"""Local restart respects real Redis ownership without controlling application services."""

import shutil
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

import restart_api
from oldaplib.test import test_mutation_gate as gate_fixture
from oldaplib.src.mutation_gate import (
    GATE_KEY,
    MutationGateUnavailable,
    mutation_gate,
    mark_gate_uncertain,
)

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or not shutil.which("redis-server"),
    reason="Native macOS and isolated Redis required",
)


@pytest.fixture
def client():
    """Own an isolated AOF store for each restart scenario."""
    gate_fixture.MutationGateTest.setUpClass()
    try:
        yield gate_fixture.MutationGateTest.client
    finally:
        gate_fixture.MutationGateTest.tearDownClass()


def test_occupied_writer_is_preserved_without_service_control(client):
    with mutation_gate(client=client):
        mark_gate_uncertain()
    original = client.get(GATE_KEY)
    domain = Mock()
    with pytest.raises(MutationGateUnavailable):
        restart_api.restart(domain, client, {"label": "fixture", "plist": "/fixture"})
    domain.identity.assert_not_called()
    domain.run.assert_not_called()
    assert client.get(GATE_KEY) == original


@pytest.mark.parametrize("fails", [False, True])
def test_restart_holds_gate_and_retains_it_on_uncertain_control(client, fails):
    domain = Mock(target="gui/fixture")
    domain.identity.side_effect = [{"pid": 123}, {"pid": 123}, {"pid": 456}]

    def control(*args):
        assert client.get(GATE_KEY) is not None
        if fails:
            raise TimeoutError("Uncertain runtime command")

    domain.run.side_effect = control
    queue = MagicMock()
    queue.control.side_effect = [
        [],
        [SimpleNamespace(fflags=restart_api.select.KQ_NOTE_EXIT)],
    ]
    with (
        patch.object(restart_api.select, "kqueue", return_value=queue),
        patch.object(
            restart_api.subprocess, "run", return_value=SimpleNamespace(returncode=113)
        ),
        patch.object(
            restart_api.requests, "get", return_value=SimpleNamespace(status_code=401)
        ),
    ):
        if fails:
            with pytest.raises(TimeoutError):
                restart_api.restart(
                    domain, client, {"label": "fixture", "plist": "/fixture"}
                )
        else:
            restart_api.restart(
                domain, client, {"label": "fixture", "plist": "/fixture"}
            )
    assert (client.get(GATE_KEY) is not None) == fails
