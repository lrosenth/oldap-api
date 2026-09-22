"""HTTP contract tests without GraphDB/index writes."""
from unittest.mock import Mock, patch
import pytest
from flask import Flask
from oldap_api.views.lucene_views import lucene_bp
from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists, OldapErrorNoPermission


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(lucene_bp)
    return app.test_client()


def test_auth_required(client):
    assert client.get("/admin/lucene/demo").status_code == 401
    assert client.put("/admin/lucene/demo", json={}).status_code == 401


def test_read_absence_and_replace_contract(client):
    service = Mock(name="connector")
    service.name = "demo"
    service.read.return_value = None
    service.apply.return_value = "created"
    with patch("oldap_api.authentication.Connection"), patch("oldaplib.src.lucene_connector.ProjectLuceneConnector", return_value=service):
        headers = {"Authorization": "Bearer token"}
        response = client.get("/admin/lucene/demo", headers=headers)
        assert response.json == {"name": "demo", "configuration": None, "revision": None}
        assert client.put("/admin/lucene/demo", headers=headers, json={"mode": "replace", "configuration": {}}).status_code == 400
        service.apply.assert_not_called()
        response = client.put("/admin/lucene/demo", headers=headers, json={"mode": "replace", "configuration": {}, "expectedRevision": None})
        assert response.status_code == 200
        service.apply.assert_called_once_with({}, mode="replace", expected_revision=None)


@pytest.mark.parametrize("error,status", [(OldapErrorNoPermission("denied"), 403), (OldapErrorAlreadyExists("stale"), 409)])
def test_library_errors(client, error, status):
    with patch("oldap_api.authentication.Connection"), patch("oldaplib.src.lucene_connector.ProjectLuceneConnector", side_effect=error):
        assert client.get("/admin/lucene/demo", headers={"Authorization": "Bearer token"}).status_code == status
