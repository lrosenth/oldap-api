"""HTTP contract tests for the public ZIP export endpoints."""

from datetime import UTC, datetime

from flask import Flask

from oldap_api import authentication
from oldap_api.exports.repository import (
    ExportQuotaExceededError,
    InMemoryExportJobRepository,
)
from oldap_api.exports.service import ExportJobService
from oldap_api.test.test_export_service import (
    AREA,
    EXPORT_IDS,
    FakeProfileRegistry,
    FakeProjector,
)
from oldap_api.views import export_views

NOW = datetime(2026, 8, 14, 23, 30, tzinfo=UTC)


class FakeConnection:
    userIri = "https://example.org/users/alice"
    userid = "alice"

    def __init__(self, **kwargs) -> None:
        pass


def _body(kind="STAGING_ALL"):
    return {
        "projectShortName": "museum",
        "kind": kind,
        "selectionIri": AREA,
    }


def _client(monkeypatch):
    service = ExportJobService(
        InMemoryExportJobRepository(),
        profile_registry=FakeProfileRegistry(),
        snapshot_projector=FakeProjector(),
    )
    monkeypatch.setattr(authentication, "Connection", FakeConnection)
    monkeypatch.setattr(export_views, "_service", lambda connection, **kwargs: service)
    app = Flask(__name__)
    app.register_blueprint(export_views.export_bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_estimate_create_read_list_and_delete_contract(monkeypatch) -> None:
    client = _client(monkeypatch)
    headers = {"Authorization": "Bearer valid-test-token"}

    estimate = client.post("/exports/estimate", json=_body(), headers=headers)
    assert estimate.status_code == 200
    assert estimate.json["maxArchiveBytes"] == 50_000_000_000
    assert estimate.headers["Cache-Control"] == "private, no-store"

    created = client.post("/exports", json=_body(), headers=headers)
    assert created.status_code == 202
    export_id = created.json["exportId"]
    assert created.json["state"] == "QUEUED"
    assert created.headers["Location"] == f"/exports/{export_id}"

    read = client.get(f"/exports/{export_id}", headers=headers)
    assert read.status_code == 200
    assert read.headers["ETag"] == '"0"'

    listed = client.get("/exports?state=QUEUED", headers=headers)
    assert [item["exportId"] for item in listed.json["items"]] == [export_id]

    cancelled = client.delete(
        f"/exports/{export_id}?expectedStateVersion=0", headers=headers
    )
    assert cancelled.status_code == 200
    assert cancelled.json["state"] == "CANCELLED"

    stale = client.delete(
        f"/exports/{export_id}?expectedStateVersion=0", headers=headers
    )
    assert stale.status_code == 409
    assert stale.json["code"] == "EXPORT_STATE_CONFLICT"


def test_authentication_validation_and_available_archive_contract(
    monkeypatch,
) -> None:
    client = _client(monkeypatch)
    headers = {"Authorization": "Bearer valid-test-token"}

    assert client.post("/exports", json=_body()).status_code == 401
    invalid = client.post(
        "/exports", json=_body() | {"unexpected": True}, headers=headers
    )
    assert invalid.status_code == 400
    assert invalid.json["code"] == "EXPORT_REQUEST_INVALID"
    archive = client.post(
        "/exports/estimate", json=_body("ARCHIVE_UNIT"), headers=headers
    )
    assert archive.status_code == 200
    assert archive.json["kind"] == "ARCHIVE_UNIT"
    archive_all = client.post(
        "/exports/estimate",
        json={"projectShortName": "museum", "kind": "ARCHIVE_ALL"},
        headers=headers,
    )
    assert archive_all.status_code == 200
    assert archive_all.json["kind"] == "ARCHIVE_ALL"
    unknown_query = client.get("/exports?mine=true", headers=headers)
    assert unknown_query.status_code == 400


def test_quota_exhaustion_has_a_stable_http_contract() -> None:
    app = Flask(__name__)
    with app.test_request_context("/exports", method="POST"):
        response = export_views._handle_error(
            ExportQuotaExceededError("The user's active export-job quota is full.")
        )

    assert response.status_code == 429
    assert response.json["code"] == "EXPORT_QUOTA_EXCEEDED"


def test_non_ready_download_and_hidden_missing_job(monkeypatch) -> None:
    client = _client(monkeypatch)
    headers = {"Authorization": "Bearer valid-test-token"}
    created = client.post("/exports", json=_body(), headers=headers)
    export_id = created.json["exportId"]

    download = client.post(f"/exports/{export_id}/download-capability", headers=headers)
    assert download.status_code == 409
    assert download.json["code"] == "EXPORT_STATE_CONFLICT"
    missing = client.get(f"/exports/{EXPORT_IDS[0]}", headers=headers)
    assert missing.status_code == 404
    assert missing.json["code"] == "EXPORT_NOT_FOUND"
