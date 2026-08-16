"""HTTP contract tests for internal ZIP export worker operations."""

from datetime import UTC, datetime, timedelta

import jwt
from flask import Flask

from oldap_api.exports.internal_auth import (
    EXPORT_SERVICE_AUDIENCE,
    EXPORT_SERVICE_TOKEN_TYPE,
)
from oldap_api.exports.repository import InMemoryExportJobRepository
from oldap_api.exports.service import ExportJobService
from oldap_api.exports.worker_service import ExportWorkerService
from oldap_api.test.test_export_manifest import bound_job
from oldap_api.views import export_views

SECRET = "export-service-test-secret-at-least-32-bytes"
ISSUER = "https://oldap.example.org"


def _token(*, token_type: str = EXPORT_SERVICE_TOKEN_TYPE) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "typ": token_type,
            "sub": "media-export-worker",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "iss": ISSUER,
            "aud": EXPORT_SERVICE_AUDIENCE,
        },
        SECRET,
        algorithm="HS256",
    )


def _client(monkeypatch):
    repository = InMemoryExportJobRepository()
    job, manifest = bound_job()
    repository.create_with_manifest(job, manifest)
    service = ExportWorkerService(repository)
    monkeypatch.setenv("OLDAP_EXPORT_SERVICE_JWT_SECRET", SECRET)
    monkeypatch.setenv("OLDAP_JWT_ISSUER", ISSUER)
    monkeypatch.setattr(export_views, "_internal_service", lambda: service)
    monkeypatch.setattr(export_views, "_deliver_notification", lambda job: None)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(export_views.internal_export_bp)
    app.register_blueprint(export_views.internal_export_claim_bp)
    return app.test_client(), repository


def test_claim_manifest_ready_and_cleanup_http_contract(monkeypatch) -> None:
    client, repository = _client(monkeypatch)
    headers = {"Authorization": f"Bearer {_token()}"}
    claim_response = client.post(
        "/internal/export-claims",
        json={"workerId": "worker-1", "supportedTasks": ["BUILD", "CLEANUP"]},
        headers=headers,
    )
    assert claim_response.status_code == 200
    claim = claim_response.json
    assert claim["task"] == "BUILD"

    manifest = client.get(
        f"/internal/exports/{claim['exportId']}/manifest?claimId={claim['claimId']}",
        headers=headers,
    )
    assert manifest.status_code == 200
    assert manifest.json["exportId"] == claim["exportId"]
    assert manifest.headers["Digest"].startswith("sha-256=")

    completed = datetime.now(UTC)
    ready = client.post(
        f"/internal/exports/{claim['exportId']}/result",
        json={
            "eventId": "55555555-5555-4555-8555-555555555555",
            "claimId": claim["claimId"],
            "expectedStateVersion": claim["stateVersion"],
            "manifestSha256": claim["manifestSha256"],
            "outcome": "READY",
            "completedAt": completed.isoformat().replace("+00:00", "Z"),
            "archiveSizeBytes": 10_000,
            "archiveSha256": "b" * 64,
            "artifactFinalized": True,
            "partialArtifactsDeleted": True,
        },
        headers=headers,
    )
    assert ready.status_code == 200
    assert ready.json["state"] == "READY"
    assert ready.json["notification"]["status"] == "SENT"
    assert ready.json["notification"]["forState"] == "READY"

    owner = type(
        "Connection",
        (),
        {"userIri": "https://example.org/users/alice", "userid": "alice"},
    )()
    deleting = ExportJobService(repository).delete(
        claim["exportId"],
        owner,
        expected_state_version=ready.json["stateVersion"],
    )
    cleanup_claim = client.post(
        "/internal/export-claims",
        json={"workerId": "worker-1", "supportedTasks": ["CLEANUP"]},
        headers=headers,
    ).json
    assert cleanup_claim["task"] == "CLEANUP"
    assert cleanup_claim["cleanupReason"] == "READY_DELETE"
    assert cleanup_claim["stateVersion"] == deleting.state_version + 1

    cleaned = client.post(
        f"/internal/exports/{claim['exportId']}/cleanup-result",
        json={
            "eventId": "77777777-7777-4777-8777-777777777777",
            "claimId": cleanup_claim["claimId"],
            "expectedStateVersion": cleanup_claim["stateVersion"],
            "completedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "artifactDeleted": True,
        },
        headers=headers,
    )
    assert cleaned.status_code == 200
    assert cleaned.json["state"] == "DELETED"


def test_internal_routes_require_exact_export_service_token(monkeypatch) -> None:
    client, _ = _client(monkeypatch)
    request_body = {"workerId": "worker-1", "supportedTasks": ["BUILD"]}

    missing = client.post("/internal/export-claims", json=request_body)
    assert missing.status_code == 401
    wrong_purpose = client.post(
        "/internal/export-claims",
        json=request_body,
        headers={"Authorization": f"Bearer {_token(token_type='import-service')}"},
    )
    assert wrong_purpose.status_code == 401


def test_internal_validation_and_empty_queue_contract(monkeypatch) -> None:
    client, _ = _client(monkeypatch)
    headers = {"Authorization": f"Bearer {_token()}"}
    invalid = client.post(
        "/internal/export-claims",
        json={"workerId": "bad worker", "supportedTasks": ["BUILD"]},
        headers=headers,
    )
    assert invalid.status_code == 400
    assert invalid.json["code"] == "EXPORT_REQUEST_INVALID"

    first = client.post(
        "/internal/export-claims",
        json={"workerId": "worker-1", "supportedTasks": ["BUILD"]},
        headers=headers,
    )
    assert first.json["task"] == "BUILD"
    empty = client.post(
        "/internal/export-claims",
        json={"workerId": "worker-2", "supportedTasks": ["BUILD"]},
        headers=headers,
    )
    assert empty.status_code == 200
    assert empty.json is None


def test_idle_poll_runs_one_notification_reconciliation(monkeypatch) -> None:
    client, repository = _client(monkeypatch)
    headers = {"Authorization": f"Bearer {_token()}"}
    repository._jobs.clear()
    calls = []
    monkeypatch.setattr(
        export_views,
        "_reconcile_one_notification",
        lambda service: calls.append(service),
    )

    response = client.post(
        "/internal/export-claims",
        json={"workerId": "worker-1", "supportedTasks": ["BUILD"]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json is None
    assert len(calls) == 1
