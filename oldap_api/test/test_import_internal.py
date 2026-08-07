"""Internal authentication and idempotent SIP receipt tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4, uuid5

import jwt
from flask import Flask

from oldap_api.imports.authorization import (
    AuthorizedTarget,
    TargetChild,
    TargetInspection,
)
from oldap_api.imports.capabilities import UploadCapabilityIssuer
from oldap_api.imports.domain import TargetSnapshot
from oldap_api.imports.internal_auth import IMPORT_SERVICE_AUDIENCE
from oldap_api.imports.repository import InMemoryImportJobRepository
from oldap_api.imports.service import ImportJobService
from oldap_api.views import import_views

SERVICE_SECRET = "oldap-api-test-import-service-secret-at-least-32-bytes"
UPLOAD_SECRET = "internal-test-upload-secret-at-least-thirty-two-bytes"


class FakeConnection:
    userIri = "https://example.org/users/alice"
    userid = "alice"


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


class FakeTargetInspector:
    def __init__(self, *, children=(), changed=False):
        self.children = tuple(children)
        self.changed = changed

    def inspect_target(self, target):
        snapshot = (
            TargetSnapshot(
                project_short_name=target.project_short_name,
                staging_area_iri=target.staging_area_iri,
                staging_area_name=target.staging_area_name,
                target_root_folder_iri=target.target_root_folder_iri,
                target_root_folder_name="Renamed",
            )
            if self.changed
            else target
        )
        return TargetInspection(snapshot=snapshot, children=self.children)


def _fixture(monkeypatch, *, inspector=None):
    repository = InMemoryImportJobRepository()
    service = ImportJobService(
        repository,
        FakeAuthorizer(),
        UploadCapabilityIssuer(
            secret=UPLOAD_SECRET,
            media_ingest_base_url="https://media.example.org",
        ),
        inspector or FakeTargetInspector(),
    )
    job, _ = service.create(
        FakeConnection(),
        {
            "projectShortName": "fasnacht",
            "stagingAreaIri": "https://example.org/staging/area",
            "targetRootFolderIri": "https://example.org/staging/root",
            "originalFileName": "archive.zip",
            "compressedSizeBytes": 1_000_000,
        },
    )
    monkeypatch.setattr(import_views, "_internal_service", lambda: service)
    monkeypatch.setattr(import_views, "_deliver_notification", lambda job: None)
    app = Flask(__name__)
    app.register_blueprint(import_views.internal_import_bp)
    app.register_blueprint(import_views.internal_claim_bp)
    app.config["TESTING"] = True
    return app.test_client(), job, service


def _token(**overrides) -> str:
    now = datetime.now(UTC)
    claims = {
        "typ": "import-service",
        "sub": "media-ingress",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": "https://oldap.org",
        "aud": IMPORT_SERVICE_AUDIENCE,
    }
    claims.update(overrides)
    return jwt.encode(claims, SERVICE_SECRET, algorithm="HS256")


def _event(job, *, event_id=None, sha256="a" * 64):
    return {
        "eventId": event_id or str(uuid4()),
        "storedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "sizeBytes": job.declared_compressed_size_bytes,
        "sha256": sha256,
        "uploadRequestId": str(uuid4()),
    }


def test_sip_stored_is_idempotent_and_conflicting_replay_is_rejected(monkeypatch):
    client, job, _ = _fixture(monkeypatch)
    headers = {"Authorization": f"Bearer {_token()}"}
    event = _event(job)

    accepted = client.post(
        f"/internal/imports/{job.import_id}/sip-stored",
        json=event,
        headers=headers,
    )
    assert accepted.status_code == 200
    assert accepted.json["state"] == "VALIDATING"
    assert accepted.json["stateVersion"] == 1
    assert accepted.json["actualCompressedSizeBytes"] == 1_000_000

    replay = client.post(
        f"/internal/imports/{job.import_id}/sip-stored",
        json=event,
        headers=headers,
    )
    assert replay.status_code == 200
    assert replay.json == accepted.json

    conflict = client.post(
        f"/internal/imports/{job.import_id}/sip-stored",
        json=event | {"sha256": "b" * 64},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json["code"] == "IMPORT_EVENT_CONFLICT"


def test_internal_route_rejects_missing_and_wrong_purpose_tokens(monkeypatch):
    client, job, _ = _fixture(monkeypatch)
    url = f"/internal/imports/{job.import_id}/sip-stored"

    missing = client.post(url, json=_event(job))
    assert missing.status_code == 401
    assert missing.headers["WWW-Authenticate"] == "Bearer"

    wrong_purpose = client.post(
        url,
        json=_event(job),
        headers={"Authorization": f"Bearer {_token(typ='access')}"},
    )
    assert wrong_purpose.status_code == 401

    now = datetime.now(UTC)
    access_token = jwt.encode(
        {
            "typ": "import-service",
            "sub": "media-ingress",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "iss": "https://oldap.org",
            "aud": IMPORT_SERVICE_AUDIENCE,
        },
        "oldap-api-test-access-secret-at-least-32-bytes",
        algorithm="HS256",
    )
    wrong_key = client.post(
        url,
        json=_event(job),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert wrong_key.status_code == 401


def test_idle_worker_poll_triggers_one_api_notification_reconciliation(monkeypatch):
    client, _, service = _fixture(monkeypatch)
    reconciled = []
    monkeypatch.setattr(
        import_views,
        "_reconcile_one_notification",
        lambda candidate: reconciled.append(candidate),
    )

    response = client.post(
        "/internal/import-claims",
        json={"workerId": "worker-1", "supportedTasks": ["VALIDATE"]},
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 204
    assert reconciled == [service]


def test_internal_receipt_requires_exact_declared_size(monkeypatch):
    client, job, _ = _fixture(monkeypatch)
    event = _event(job) | {"sizeBytes": job.declared_compressed_size_bytes - 1}
    response = client.post(
        f"/internal/imports/{job.import_id}/sip-stored",
        json=event,
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 409
    assert response.json["code"] == "IMPORT_EVENT_CONFLICT"


def test_cleanup_http_contract_expires_only_after_deletion_proof(monkeypatch):
    client, _, service = _fixture(monkeypatch)
    current = datetime.now(UTC)
    job, _ = service.create(
        FakeConnection(),
        {
            "projectShortName": "fasnacht",
            "stagingAreaIri": "https://example.org/staging/area",
            "targetRootFolderIri": "https://example.org/staging/root",
            "originalFileName": "abandoned.zip",
            "compressedSizeBytes": 1_000_000,
        },
        now=current - timedelta(hours=25),
    )
    headers = {"Authorization": f"Bearer {_token()}"}
    claim = client.post(
        "/internal/import-claims",
        json={"workerId": "worker-1", "supportedTasks": ["CLEANUP"]},
        headers=headers,
    )
    assert claim.status_code == 200
    assert claim.json["cleanupReason"] == "EXPIRED"

    payload = {
        "eventId": str(uuid4()),
        "claimId": claim.json["claimId"],
        "expectedStateVersion": claim.json["stateVersion"],
        "reason": "EXPIRED",
        "temporaryPayloadDeleted": True,
        "completedAt": current.isoformat().replace("+00:00", "Z"),
    }
    accepted = client.post(
        f"/internal/imports/{job.import_id}/cleanup-result",
        json=payload,
        headers=headers,
    )
    replay = client.post(
        f"/internal/imports/{job.import_id}/cleanup-result",
        json=payload,
        headers=headers,
    )

    assert accepted.status_code == replay.status_code == 200
    assert accepted.json["state"] == "EXPIRED"
    assert accepted.json["quotaReservedBytes"] == 0
    assert accepted.json["cleanupPending"] is False
    assert replay.json == accepted.json


def test_claim_bound_target_preflight_reports_blocking_and_warning_collisions(
    monkeypatch,
):
    inspector = FakeTargetInspector(
        children=(
            TargetChild(kind="folder", name="Pho\u0308tos"),
            TargetChild(kind="media", name="Notes.txt"),
        )
    )
    client, job, _ = _fixture(monkeypatch, inspector=inspector)
    headers = {"Authorization": f"Bearer {_token()}"}
    client.post(
        f"/internal/imports/{job.import_id}/sip-stored",
        json=_event(job),
        headers=headers,
    )
    claim = client.post(
        "/internal/import-claims",
        json={"workerId": "worker-1", "supportedTasks": ["VALIDATE"]},
        headers=headers,
    ).json

    response = client.post(
        f"/internal/import-claims/{claim['claimId']}/target-preflight",
        json={
            "workerId": "worker-1",
            "expectedStateVersion": claim["stateVersion"],
            "topLevelEntries": [
                {"entryIndex": 0, "name": "PHÖTOS", "entryType": "directory"},
                {"entryIndex": 1, "name": "notes.TXT", "entryType": "file"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["targetRootFolderIri"] == job.target.target_root_folder_iri
    assert response.json["findings"] == [
        {
            "blocking": True,
            "code": "TARGET_FOLDER_COLLISION",
            "entryIndex": 0,
            "existingKind": "folder",
            "existingName": "Pho\u0308tos",
        },
        {
            "blocking": False,
            "code": "TARGET_MEDIA_NAME_COLLISION",
            "entryIndex": 1,
            "existingKind": "media",
            "existingName": "Notes.txt",
        },
    ]


def test_target_preflight_detects_changed_target_and_rejects_stale_worker(monkeypatch):
    client, job, _ = _fixture(monkeypatch, inspector=FakeTargetInspector(changed=True))
    headers = {"Authorization": f"Bearer {_token()}"}
    client.post(
        f"/internal/imports/{job.import_id}/sip-stored",
        json=_event(job),
        headers=headers,
    )
    claim = client.post(
        "/internal/import-claims",
        json={"workerId": "worker-1", "supportedTasks": ["VALIDATE"]},
        headers=headers,
    ).json
    payload = {
        "workerId": "worker-1",
        "expectedStateVersion": claim["stateVersion"],
        "topLevelEntries": [
            {"entryIndex": 0, "name": "Photos", "entryType": "directory"}
        ],
    }

    changed = client.post(
        f"/internal/import-claims/{claim['claimId']}/target-preflight",
        json=payload,
        headers=headers,
    )
    stale = client.post(
        f"/internal/import-claims/{claim['claimId']}/target-preflight",
        json=payload | {"workerId": "worker-2"},
        headers=headers,
    )

    assert changed.status_code == 200
    assert changed.json["findings"] == [{"blocking": True, "code": "TARGET_CHANGED"}]
    assert stale.status_code == 409
    assert stale.json["code"] == "IMPORT_CLAIM_CONFLICT"


def test_single_worker_claim_heartbeat_and_ready_result(monkeypatch):
    client, job, _ = _fixture(monkeypatch)
    headers = {"Authorization": f"Bearer {_token()}"}
    stored = client.post(
        f"/internal/imports/{job.import_id}/sip-stored",
        json=_event(job),
        headers=headers,
    )
    assert stored.status_code == 200

    claim = client.post(
        "/internal/import-claims",
        json={
            "workerId": "worker-1",
            "supportedTasks": ["VALIDATE", "IMPORT", "CLEANUP"],
            "requestedLeaseSeconds": 300,
        },
        headers=headers,
    )
    assert claim.status_code == 200
    assert claim.json["task"] == "VALIDATE"
    assert claim.json["stateVersion"] == 2
    assert claim.json["jobCreatedAt"] == job.created_at.isoformat().replace(
        "+00:00", "Z"
    )
    assert claim.json["requestedByIri"] == job.requested_by_iri
    assert claim.json["originalFileName"] == job.original_file_name
    assert claim.json["compressedSizeBytes"] == job.declared_compressed_size_bytes

    no_second_claim = client.post(
        "/internal/import-claims",
        json={"workerId": "worker-2", "supportedTasks": ["VALIDATE"]},
        headers=headers,
    )
    assert no_second_claim.status_code == 204

    wrong_worker = client.post(
        f"/internal/import-claims/{claim.json['claimId']}/heartbeat",
        json={"workerId": "worker-2", "expectedStateVersion": 2},
        headers=headers,
    )
    assert wrong_worker.status_code == 409
    assert wrong_worker.json["code"] == "IMPORT_CLAIM_CONFLICT"

    heartbeat = client.post(
        f"/internal/import-claims/{claim.json['claimId']}/heartbeat",
        json={"workerId": "worker-1", "expectedStateVersion": 2},
        headers=headers,
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json["claimId"] == claim.json["claimId"]

    result = _validation_result(claim.json, extracted_bytes=20_000_000)
    ready = client.post(
        f"/internal/imports/{job.import_id}/validation-result",
        json=result,
        headers=headers,
    )
    assert ready.status_code == 200
    assert ready.json["state"] == "READY"
    assert ready.json["stateVersion"] == 3
    assert ready.json["quotaReservedBytes"] == 20_000_000
    assert ready.json["reportAvailable"] is True
    assert ready.json["canConfirm"] is True
    assert "expiresAt" in ready.json
    assert ready.json["notification"] == {
        "status": "SENT",
        "forState": "READY",
        "attempts": 1,
        "sentAt": ready.json["notification"]["sentAt"],
    }

    replay = client.post(
        f"/internal/imports/{job.import_id}/validation-result",
        json=result,
        headers=headers,
    )
    assert replay.status_code == 200
    assert replay.json == ready.json

    conflict = client.post(
        f"/internal/imports/{job.import_id}/validation-result",
        json=result | {"reportSha256": "d" * 64},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json["code"] == "IMPORT_EVENT_CONFLICT"


def test_invalid_result_requires_deleted_payload_and_releases_quota(monkeypatch):
    client, job, _ = _fixture(monkeypatch)
    headers = {"Authorization": f"Bearer {_token()}"}
    client.post(
        f"/internal/imports/{job.import_id}/sip-stored",
        json=_event(job),
        headers=headers,
    )
    claim = client.post(
        "/internal/import-claims",
        json={"workerId": "worker-1", "supportedTasks": ["VALIDATE"]},
        headers=headers,
    ).json
    result = _validation_result(claim, extracted_bytes=10_000_000)
    result["outcome"] = "INVALID"
    result["temporaryPayloadDeleted"] = True
    result["summary"]["errorCount"] = 1
    result["summary"]["rejectedEntries"] = 1

    invalid = client.post(
        f"/internal/imports/{job.import_id}/validation-result",
        json=result,
        headers=headers,
    )
    assert invalid.status_code == 200
    assert invalid.json["state"] == "INVALID"
    assert invalid.json["quotaReservedBytes"] == 0
    assert invalid.json["cleanupPending"] is False
    assert invalid.json["reportAvailable"] is True


def test_mail_failure_never_rolls_back_ready_and_retries_are_bounded(monkeypatch):
    client, job, _ = _fixture(monkeypatch)
    headers = {"Authorization": f"Bearer {_token()}"}
    client.post(
        f"/internal/imports/{job.import_id}/sip-stored",
        json=_event(job),
        headers=headers,
    )
    claim = client.post(
        "/internal/import-claims",
        json={"workerId": "worker-1", "supportedTasks": ["VALIDATE"]},
        headers=headers,
    ).json
    result = _validation_result(claim, extracted_bytes=10_000_000)
    attempts = []

    def fail_mail(job):
        attempts.append(job.import_id)
        raise RuntimeError("SMTP password must not be persisted")

    monkeypatch.setattr(import_views, "_deliver_notification", fail_mail)
    responses = [
        client.post(
            f"/internal/imports/{job.import_id}/validation-result",
            json=result,
            headers=headers,
        )
        for _ in range(4)
    ]

    assert all(response.status_code == 200 for response in responses)
    assert all(response.json["state"] == "READY" for response in responses)
    assert len(attempts) == 3
    assert responses[-1].json["notification"] == {
        "status": "FAILED",
        "forState": "READY",
        "attempts": 3,
    }


def test_internal_commit_route_is_claim_bound_and_exactly_replayable(monkeypatch):
    client, job, service = _fixture(monkeypatch)
    headers = {"Authorization": f"Bearer {_token()}"}
    client.post(
        f"/internal/imports/{job.import_id}/sip-stored",
        json=_event(job),
        headers=headers,
    )
    validation_claim = client.post(
        "/internal/import-claims",
        json={"workerId": "worker-1", "supportedTasks": ["VALIDATE"]},
        headers=headers,
    ).json
    ready = client.post(
        f"/internal/imports/{job.import_id}/validation-result",
        json=_validation_result(validation_claim, extracted_bytes=20_000_000),
        headers=headers,
    ).json
    service.confirm(
        job.import_id,
        FakeConnection(),
        expected_state_version=ready["stateVersion"],
    )
    import_claim = client.post(
        "/internal/import-claims",
        json={"workerId": "worker-1", "supportedTasks": ["IMPORT"]},
        headers=headers,
    ).json
    namespace = UUID(job.import_id)
    payload = {
        "eventId": str(uuid4()),
        "claimId": import_claim["claimId"],
        "expectedStateVersion": import_claim["stateVersion"],
        "manifestSha256": import_claim["manifestSha256"],
        "folders": [
            {
                "entryIndex": 0,
                "relativePath": "Fotos",
                "parentRelativePath": "",
                "name": "Fotos",
            }
        ],
        "media": [
            {
                "entryIndex": 1,
                "relativePath": "Fotos/Bild.jpg",
                "parentRelativePath": "Fotos",
                "assetId": str(uuid5(namespace, "entry:1")),
                "checksumSha256": "d" * 64,
                "originalName": "Bild.jpg",
                "originalMimeType": "image/jpeg",
                "dctermsType": "dcmitype:StillImage",
                "protocol": "iiif",
                "derivativeName": "master.tif",
                "storagePath": "fasnacht/image",
            }
        ],
    }

    accepted = client.post(
        f"/internal/imports/{job.import_id}/commit", json=payload, headers=headers
    )
    replay = client.post(
        f"/internal/imports/{job.import_id}/commit", json=payload, headers=headers
    )

    assert accepted.status_code == replay.status_code == 200
    assert accepted.json == replay.json
    assert accepted.json["job"]["state"] == "IMPORTED"
    assert accepted.json["job"]["cleanupPending"] is True
    assert accepted.json["resources"][1]["assetId"] == payload["media"][0]["assetId"]


def _validation_result(claim: dict, *, extracted_bytes: int) -> dict:
    return {
        "eventId": str(uuid4()),
        "claimId": claim["claimId"],
        "expectedStateVersion": claim["stateVersion"],
        "outcome": "READY",
        "completedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "temporaryPayloadDeleted": False,
        "manifestSha256": "b" * 64,
        "reportSha256": "c" * 64,
        "summary": {
            "entriesObserved": 4,
            "inventoryComplete": True,
            "files": 2,
            "directories": 2,
            "importableFiles": 2,
            "importableDirectories": 2,
            "ignoredEntries": 0,
            "rejectedEntries": 0,
            "warningCount": 0,
            "errorCount": 0,
            "compressedBytes": 1_000_000,
            "extractedBytes": extracted_bytes,
            "maxDepth": 2,
        },
    }
