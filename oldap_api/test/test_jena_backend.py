"""Backend selection and the private, database-free identity boundary."""

from unittest.mock import patch

import pytest
from flask import Flask
from oldap_api.backend import backend_name, create_connection, validate_backend
from oldap_api.views.jena_identity_views import jena_identity_bp
from oldaplib.src.helpers.oldaperror import OldapErrorConfiguration


def test_default_keeps_graphdb_constructor(monkeypatch):
    monkeypatch.delenv("OLDAP_BACKEND", raising=False)
    with patch("oldap_api.backend.GraphDBConnection") as constructor:
        assert create_connection(token="owned-token") is constructor.return_value
        constructor.assert_called_once_with(token="owned-token")


def test_unknown_backend_fails_explicitly(monkeypatch):
    monkeypatch.setenv("OLDAP_BACKEND", "jenna")
    with pytest.raises(OldapErrorConfiguration):
        backend_name()


def test_jena_requires_private_identity_key(monkeypatch):
    monkeypatch.setenv("OLDAP_BACKEND", "jena")
    monkeypatch.delenv("OLDAP_JENA_IDENTITY_KEY", raising=False)
    with patch("oldaplib.src.jena_connection.JenaSettings.from_environment"):
        with pytest.raises(OldapErrorConfiguration, match="identity"):
            validate_backend()


def test_identity_is_private_and_does_not_build_connection(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(jena_identity_bp)
    client = app.test_client()
    monkeypatch.setenv("OLDAP_BACKEND", "graphdb")
    assert client.post("/internal/jena/identity").status_code == 404
    monkeypatch.setenv("OLDAP_BACKEND", "jena")
    monkeypatch.setenv("OLDAP_JENA_IDENTITY_KEY", "owned-key")
    assert (
        client.post("/internal/jena/identity", data={"token": "invalid"}).status_code
        == 401
    )
    with patch(
        "oldap_api.views.jena_identity_views.TokenCodec.from_environment"
    ) as codec:
        codec.return_value.decode_access_token.side_effect = OldapErrorConfiguration(
            "invalid"
        )
        response = client.post(
            "/internal/jena/identity",
            data={"token": "invalid"},
            headers={"Authorization": "Bearer owned-key"},
        )
        assert response.json == {"active": False}
        assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("backend", ["graphdb", "jena"])
@pytest.mark.parametrize(
    "module_name,function_name,prefix",
    [
        ("export_views", "_export_service_connection", "EXPORT"),
        ("import_views", "_import_service_connection", "IMPORT"),
        ("mobile_media_views", "_internal_service", "MOBILE_MEDIA"),
        ("mobile_media_lifecycle_views", "_outbox", "MOBILE_MEDIA"),
    ],
)
def test_internal_service_connections_authenticate_for_selected_backend(
    monkeypatch, backend, module_name, function_name, prefix
):
    """Internal workers need Jena transport tokens without changing GraphDB."""
    import importlib

    module = importlib.import_module("oldap_api.views." + module_name)
    monkeypatch.setenv("OLDAP_BACKEND", backend)
    monkeypatch.setenv("OLDAP_" + prefix + "_SERVICE_USER", "service-test")
    monkeypatch.setenv("OLDAP_" + prefix + "_SERVICE_PASSWORD", "fixture-password")
    with patch.object(module, "Connection") as connection:
        getattr(module, function_name)()
        assert connection.call_args.kwargs["issue_access_token"] is (backend == "jena")
        assert connection.call_args.kwargs["userId"] == "service-test"


@pytest.mark.parametrize("authorization", ["", "Bearer wrong", "Bearer ä"])
def test_identity_rejects_invalid_credentials_without_decoding(
    monkeypatch, authorization
):
    """Malformed credentials must return 401, including non-ASCII header values."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(jena_identity_bp)
    monkeypatch.setenv("OLDAP_BACKEND", "jena")
    monkeypatch.setenv("OLDAP_JENA_IDENTITY_KEY", "owned-key")
    with patch(
        "oldap_api.views.jena_identity_views.TokenCodec.from_environment"
    ) as codec:
        response = app.test_client().post(
            "/internal/jena/identity",
            data={"token": "invalid"},
            headers={"Authorization": authorization},
        )
    assert response.status_code == 401
    codec.assert_not_called()
