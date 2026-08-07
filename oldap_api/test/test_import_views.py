"""HTTP contract tests for the public ZIP import endpoints."""

import json
from datetime import UTC, datetime

from flask import Flask

from oldap_api import authentication
from oldap_api.imports.authorization import AuthorizedTarget
from oldap_api.imports.capabilities import UploadCapabilityIssuer
from oldap_api.imports.domain import TargetSnapshot
from oldap_api.imports.repository import InMemoryImportJobRepository
from oldap_api.imports.service import ImportJobService
from oldap_api.views import import_views

SECRET = "view-import-upload-secret-at-least-thirty-two-bytes"


class FakeConnection:
    userIri = "https://example.org/users/alice"
    userid = "alice"

    def __init__(self, **kwargs) -> None:
        pass


class FakeAuthorizer:
    def authorize_target(self, connection, **kwargs):
        return AuthorizedTarget(
            TargetSnapshot(
                project_short_name="fasnacht",
                staging_area_iri="https://example.org/staging/area",
                staging_area_name="Area",
                target_root_folder_iri="https://example.org/staging/root",
                target_root_folder_name="Root",
            ),
            3_000_000_000,
        )


def _client(monkeypatch):
    repository = InMemoryImportJobRepository()
    service = ImportJobService(
        repository,
        FakeAuthorizer(),
        UploadCapabilityIssuer(
            secret=SECRET,
            media_ingest_base_url="https://media.example.org",
        ),
    )
    monkeypatch.setattr(authentication, "Connection", FakeConnection)
    monkeypatch.setattr(import_views, "_service", lambda connection: service)
    app = Flask(__name__)
    app.register_blueprint(import_views.import_bp)
    app.config["TESTING"] = True
    return app.test_client()


def _body():
    return {
        "projectShortName": "fasnacht",
        "stagingAreaIri": "https://example.org/staging/area",
        "targetRootFolderIri": "https://example.org/staging/root",
        "originalFileName": "archive.zip",
        "compressedSizeBytes": 1_000_000,
    }


def test_create_read_list_reissue_and_cancel_contract(monkeypatch):
    client = _client(monkeypatch)
    headers = {"Authorization": "Bearer valid-test-token"}

    created = client.post("/imports", json=_body(), headers=headers)
    assert created.status_code == 201
    assert created.headers["Cache-Control"] == "no-store"
    import_id = created.json["job"]["importId"]
    assert created.json["job"]["state"] == "UPLOADING"
    assert created.json["upload"]["bearerToken"]

    read = client.get(f"/imports/{import_id}", headers=headers)
    assert read.status_code == 200
    assert read.headers["ETag"] == '"0"'

    listed = client.get("/imports?state=UPLOADING", headers=headers)
    assert [item["importId"] for item in listed.json["items"]] == [import_id]

    reissued = client.post(
        f"/imports/{import_id}/upload-capability",
        json={"expectedStateVersion": 0},
        headers=headers,
    )
    assert reissued.status_code == 200
    assert reissued.headers["Cache-Control"] == "no-store"

    cancelled = client.post(
        f"/imports/{import_id}/cancel",
        json={"expectedStateVersion": 0},
        headers=headers,
    )
    assert cancelled.status_code == 202
    assert cancelled.json["state"] == "CANCELLED"
    assert cancelled.json["quotaReservedBytes"] == 0

    stale = client.post(
        f"/imports/{import_id}/cancel",
        json={"expectedStateVersion": 0},
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.json["code"] == "IMPORT_VERSION_CONFLICT"


def test_create_accepts_canonical_oldap_uuid_urn_targets(monkeypatch):
    """OLDAP-generated staging resources use canonical urn:uuid identifiers."""
    client = _client(monkeypatch)
    body = _body() | {
        "stagingAreaIri": "urn:uuid:e1c03947-4f53-465f-85c5-0296e12bd0cc",
        "targetRootFolderIri": "urn:uuid:30aba28d-e931-48e9-bfd8-230f9e147f23",
    }

    response = client.post(
        "/imports",
        json=body,
        headers={"Authorization": "Bearer valid-test-token"},
    )

    assert response.status_code == 201
    assert response.json["job"]["state"] == "UPLOADING"


def test_authentication_and_closed_request_validation(monkeypatch):
    client = _client(monkeypatch)
    missing_auth = client.post("/imports", json=_body())
    assert missing_auth.status_code == 401

    invalid = _body() | {"unexpected": True}
    response = client.post(
        "/imports",
        json=invalid,
        headers={"Authorization": "Bearer valid-test-token"},
    )
    assert response.status_code == 400
    assert response.json["code"] == "IMPORT_REQUEST_INVALID"

    oversized = _body() | {"compressedSizeBytes": 500_000_001}
    response = client.post(
        "/imports",
        json=oversized,
        headers={"Authorization": "Bearer valid-test-token"},
    )
    assert response.status_code == 413
    assert response.json["code"] == "UPLOAD_SIZE_LIMIT"

    for unsafe_iri in (
        "urn:uuid:not-a-uuid",
        "urn:isbn:9783161484100",
        "file:///tmp/staging-area",
        "data:text/plain,staging-area",
        "javascript:alert(1)",
    ):
        response = client.post(
            "/imports",
            json=_body() | {"stagingAreaIri": unsafe_iri},
            headers={"Authorization": "Bearer valid-test-token"},
        )
        assert response.status_code == 400
        assert response.json["code"] == "IMPORT_REQUEST_INVALID"


def test_list_uses_opaque_cursor_and_rejects_unknown_query_fields(monkeypatch):
    client = _client(monkeypatch)
    headers = {"Authorization": "Bearer valid-test-token"}
    created_ids = {
        client.post("/imports", json=_body(), headers=headers).json["job"]["importId"]
        for _ in range(3)
    }

    first = client.get("/imports?limit=2", headers=headers)
    assert first.status_code == 200
    assert len(first.json["items"]) == 2
    assert first.json["nextCursor"]

    second = client.get(
        "/imports",
        query_string={"limit": 2, "cursor": first.json["nextCursor"]},
        headers=headers,
    )
    returned_ids = {
        item["importId"] for item in first.json["items"] + second.json["items"]
    }
    assert second.status_code == 200
    assert "nextCursor" not in second.json
    assert returned_ids == created_ids

    invalid = client.get("/imports?cursor=not-a-cursor", headers=headers)
    assert invalid.status_code == 400
    unknown = client.get("/imports?filename=secret.zip", headers=headers)
    assert unknown.status_code == 400


def test_report_endpoint_is_private_and_never_exposes_records_token(monkeypatch):
    client = _client(monkeypatch)
    headers = {"Authorization": "Bearer valid-test-token"}
    created = client.post("/imports", json=_body(), headers=headers)
    import_id = created.json["job"]["importId"]

    class FakeRecordClient:
        def get_report(self, job):
            assert job.import_id == import_id
            return {
                "documentType": "oldap.zip-import.report",
                "schemaVersion": "1.0.0",
                "importId": import_id,
                "status": "READY",
            }

    monkeypatch.setattr(import_views, "_record_client", FakeRecordClient)
    response = client.get(f"/imports/{import_id}/report", headers=headers)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.json["importId"] == import_id
    assert "token" not in json.dumps(response.json).lower()
