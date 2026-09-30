"""Offline worker lifecycle checks; never contact shared services."""
from contextlib import contextmanager
from unittest.mock import Mock

from flask import Flask
import pytest
import oldap_api


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    app = Flask(__name__)
    monkeypatch.setattr(oldap_api, "factory", lambda: app)
    monkeypatch.setattr("oldap_api.config.Dev.UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr("oldap_api.config.Dev.TMP_FOLDER", str(tmp_path / "tmp"))
    monkeypatch.setenv("APP_ENV", "Dev")
    monkeypatch.setattr(oldap_api, "validate_redis_database_separation", Mock())
    connection, cache = Mock(), Mock()
    monkeypatch.setattr(oldap_api, "Connection", connection)
    monkeypatch.setattr(oldap_api, "CacheSingletonRedis", cache)
    return app, connection, cache


def test_startup_initializes_context_without_clearing_cache(runtime):
    app, connection, cache = runtime
    assert oldap_api.create_app() is app
    connection.assert_called_once_with(context_name="DEFAULT")
    cache.assert_not_called()


def test_bootstrap_failure_prevents_worker_readiness(runtime):
    _, connection, cache = runtime
    connection.side_effect = RuntimeError("GraphDB unavailable")
    with pytest.raises(RuntimeError, match="GraphDB unavailable"):
        oldap_api.create_app()
    cache.assert_not_called()


def test_explicit_invalidation_holds_writer_gate(runtime, monkeypatch):
    app, _, cache = runtime
    held = []
    @contextmanager
    def gate(*, wait_seconds):
        assert wait_seconds == 0
        held.append(True)
        try:
            yield
        finally:
            held.pop()
    monkeypatch.setattr(oldap_api, "mutation_gate", gate)
    cache.return_value.clear.side_effect = lambda: held[0]
    oldap_api.create_app()
    result = app.test_cli_runner().invoke(args=["clear-object-cache"])
    assert result.exit_code == 0, result.output
    cache.return_value.clear.assert_called_once()
    assert not held


def test_occupied_writer_prevents_invalidation(runtime, monkeypatch):
    app, _, cache = runtime
    @contextmanager
    def gate(**kwargs):
        raise RuntimeError("Writer busy")
        yield
    monkeypatch.setattr(oldap_api, "mutation_gate", gate)
    oldap_api.create_app()
    result = app.test_cli_runner().invoke(args=["clear-object-cache"])
    assert result.exit_code != 0
    cache.assert_not_called()
