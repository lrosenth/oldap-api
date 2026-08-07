"""Focused lifecycle, quota, and capability tests for ZIP imports."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4, uuid5

import jwt
import pytest

from oldap_api.imports.authorization import AuthorizedTarget
from oldap_api.imports.capabilities import (
    UPLOAD_TOKEN_AUDIENCE,
    UploadCapabilityIssuer,
)
from oldap_api.imports.domain import (
    ImportClaimConflict,
    ImportState,
    ImportStateConflict,
    ImportVersionConflict,
    NotificationStatus,
    TargetSnapshot,
    conservative_quota_reservation,
)
from oldap_api.imports.repository import (
    ImportNotFoundError,
    ImportQuotaExceededError,
    InMemoryImportJobRepository,
)
from oldap_api.imports.service import ImportJobService

SECRET = "import-upload-test-secret-at-least-thirty-two-bytes"


class FakeConnection:
    """Minimal authenticated identity consumed by the application service."""

    def __init__(self, user_iri: str = "https://example.org/users/alice") -> None:
        self.userIri = user_iri
        self.userid = user_iri.rsplit("/", 1)[-1]


class FakeAuthorizer:
    """Return a stable authorized target with a configurable quota."""

    def __init__(self, quota: int = 3_000_000_000) -> None:
        self.quota = quota
        self.snapshot = TargetSnapshot(
            project_short_name="fasnacht",
            staging_area_iri="https://example.org/staging/area",
            staging_area_name="Main staging area",
            target_root_folder_iri="https://example.org/staging/root",
            target_root_folder_name="Root",
        )

    def authorize_target(self, connection, **kwargs) -> AuthorizedTarget:
        return AuthorizedTarget(self.snapshot, self.quota)


def _service(
    repository: InMemoryImportJobRepository | None = None,
    authorizer: FakeAuthorizer | None = None,
) -> ImportJobService:
    return ImportJobService(
        repository or InMemoryImportJobRepository(),
        authorizer or FakeAuthorizer(),
        UploadCapabilityIssuer(
            secret=SECRET,
            media_ingest_base_url="https://media.example.org",
            issuer="https://api.example.org",
        ),
    )


def _request(size: int = 10_000_000) -> dict[str, object]:
    return {
        "projectShortName": "fasnacht",
        "stagingAreaIri": "https://example.org/staging/area",
        "targetRootFolderIri": "https://example.org/staging/root",
        "originalFileName": "Ba\u0308r.zip",
        "compressedSizeBytes": size,
    }


def test_create_reserves_conservative_quota_and_issues_scoped_token():
    current = datetime.now(UTC)
    job, upload = _service().create(FakeConnection(), _request(), now=current)

    assert job.state is ImportState.UPLOADING
    assert job.state_version == 0
    assert job.original_file_name == "Bär.zip"
    assert job.quota_reserved_bytes == 500_000_000
    assert upload.url == f"https://media.example.org/imports/{job.import_id}/sip"

    claims = jwt.decode(
        upload.bearer_token,
        SECRET,
        algorithms=["HS256"],
        audience=UPLOAD_TOKEN_AUDIENCE,
        issuer="https://api.example.org",
    )
    assert claims["typ"] == "ingest-upload"
    assert claims["importId"] == job.import_id
    assert claims["sub"] == job.requested_by_iri
    assert claims["maxBytes"] == 500_000_000


def test_creation_quota_check_is_repository_atomic():
    repository = InMemoryImportJobRepository()
    service = _service(repository, FakeAuthorizer(quota=700_000_000))
    service.create(FakeConnection(), _request())

    with pytest.raises(ImportQuotaExceededError):
        service.create(FakeConnection(), _request())


def test_concurrent_creation_cannot_overreserve_staging_quota():
    repository = InMemoryImportJobRepository()
    service = _service(repository, FakeAuthorizer(quota=700_000_000))
    barrier = Barrier(2)

    def create_after_barrier():
        barrier.wait()
        try:
            return service.create(FakeConnection(), _request())[0]
        except ImportQuotaExceededError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create_after_barrier(), range(2)))

    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert sum(isinstance(result, ImportQuotaExceededError) for result in results) == 1


def test_concurrent_workers_can_claim_only_one_global_task() -> None:
    """Simultaneous workers cannot bypass the global single-job lease."""

    service = _service()
    job, _ = service.create(FakeConnection(), _request(size=1_000_000))
    current = datetime.now(UTC)
    service.record_sip_stored(
        job.import_id,
        {
            "eventId": str(uuid4()),
            "storedAt": current.isoformat(),
            "sizeBytes": 1_000_000,
            "sha256": "a" * 64,
            "uploadRequestId": str(uuid4()),
        },
    )
    barrier = Barrier(2)

    def claim(worker_id: str):
        barrier.wait()
        return service.claim_next(
            {"workerId": worker_id, "supportedTasks": ["VALIDATE"]},
            now=current,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, ("worker-1", "worker-2")))

    assert sum(result is not None for result in results) == 1
    assert sum(result is None for result in results) == 1


def test_cancel_releases_quota_and_rejects_stale_action():
    service = _service()
    connection = FakeConnection()
    job, _ = service.create(connection, _request())

    cancelled = service.cancel(
        job.import_id,
        connection,
        expected_state_version=0,
    )
    assert cancelled.state is ImportState.CANCELLED
    assert cancelled.state_version == 1
    assert cancelled.quota_reserved_bytes == 0
    assert cancelled.cleanup_pending is True

    with pytest.raises(ImportVersionConflict):
        service.cancel(job.import_id, connection, expected_state_version=0)


def test_cross_user_reads_are_indistinguishable_from_missing_jobs():
    service = _service()
    job, _ = service.create(FakeConnection(), _request())

    with pytest.raises(ImportNotFoundError):
        service.get_for_user(
            job.import_id,
            FakeConnection("https://example.org/users/bob"),
        )


def test_only_ready_unexpired_job_can_be_confirmed():
    repository = InMemoryImportJobRepository()
    authorizer = FakeAuthorizer()
    service = _service(repository, authorizer)
    connection = FakeConnection()
    uploading, _ = service.create(connection, _request())

    with pytest.raises(ImportStateConflict):
        service.confirm(
            uploading.import_id,
            connection,
            expected_state_version=0,
        )

    current = datetime.now(UTC)
    validating = uploading.transition(
        ImportState.VALIDATING,
        expected_state_version=0,
        now=current,
    )
    ready = validating.transition(
        ImportState.READY,
        expected_state_version=1,
        now=current,
        expires_at=current + timedelta(days=7),
    )
    repository.replace(ready, expected_state_version=0)

    importing = service.confirm(
        ready.import_id,
        connection,
        expected_state_version=2,
        now=current,
    )
    assert importing.state is ImportState.IMPORTING
    assert importing.state_version == 3


def test_expired_ready_job_cannot_be_confirmed():
    repository = InMemoryImportJobRepository()
    service = _service(repository)
    connection = FakeConnection()
    uploading, _ = service.create(connection, _request())
    current = datetime.now(UTC)
    validating = uploading.transition(
        ImportState.VALIDATING,
        expected_state_version=0,
        now=current - timedelta(days=8),
    )
    expired = validating.transition(
        ImportState.READY,
        expected_state_version=1,
        now=current - timedelta(days=7),
        expires_at=current - timedelta(seconds=1),
    )
    repository.replace(expired, expected_state_version=0)

    with pytest.raises(ImportStateConflict, match="expired"):
        service.confirm(
            expired.import_id,
            connection,
            expected_state_version=2,
            now=current,
        )


def test_concurrent_ready_actions_have_one_authoritative_winner() -> None:
    """Two confirmations of one reviewed version cannot queue two imports."""

    repository = InMemoryImportJobRepository()
    service = _service(repository)
    connection = FakeConnection()
    uploading, _ = service.create(connection, _request())
    current = datetime.now(UTC)
    ready = uploading.transition(
        ImportState.VALIDATING, expected_state_version=0, now=current
    ).transition(
        ImportState.READY,
        expected_state_version=1,
        now=current,
        expires_at=current + timedelta(days=7),
    )
    repository.replace(ready, expected_state_version=0)
    barrier = Barrier(2)

    def confirm_after_barrier(_: int):
        barrier.wait()
        try:
            return service.confirm(
                ready.import_id,
                connection,
                expected_state_version=ready.state_version,
                now=current,
            )
        except (ImportStateConflict, ImportVersionConflict) as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(confirm_after_barrier, range(2)))

    assert (
        sum(
            not isinstance(result, Exception) and result.state is ImportState.IMPORTING
            for result in results
        )
        == 1
    )
    assert sum(isinstance(result, Exception) for result in results) == 1
    assert repository.get(ready.import_id).state is ImportState.IMPORTING


def test_quota_reservation_is_bounded_by_extracted_limit():
    assert conservative_quota_reservation(1) == 50
    assert conservative_quota_reservation(100_000_000) == 3_000_000_000
    with pytest.raises(ValueError):
        conservative_quota_reservation(500_000_001)


def test_expired_worker_lease_can_be_reclaimed_but_active_lease_is_global():
    service = _service()
    connection = FakeConnection()
    job, _ = service.create(connection, _request(size=1_000_000))
    current = datetime.now(UTC)
    service.record_sip_stored(
        job.import_id,
        {
            "eventId": "11111111-1111-4111-8111-111111111111",
            "storedAt": current.isoformat(),
            "sizeBytes": 1_000_000,
            "sha256": "a" * 64,
            "uploadRequestId": "22222222-2222-4222-8222-222222222222",
        },
    )

    first = service.claim_next(
        {
            "workerId": "worker-1",
            "supportedTasks": ["VALIDATE"],
            "requestedLeaseSeconds": 60,
        },
        now=current,
    )
    assert first is not None
    assert (
        service.claim_next(
            {"workerId": "worker-2", "supportedTasks": ["VALIDATE"]},
            now=current + timedelta(seconds=59),
        )
        is None
    )

    reclaimed = service.claim_next(
        {"workerId": "worker-2", "supportedTasks": ["VALIDATE"]},
        now=current + timedelta(seconds=61),
    )
    assert reclaimed is not None
    assert reclaimed.claim_id != first.claim_id
    assert reclaimed.state_version == first.state_version + 1


def _cleanup_payload(claim, now: datetime) -> dict[str, object]:
    return {
        "eventId": str(uuid4()),
        "claimId": claim.claim_id,
        "expectedStateVersion": claim.state_version,
        "reason": claim.cleanup_reason,
        "temporaryPayloadDeleted": True,
        "completedAt": now.isoformat(),
    }


def test_stale_upload_expires_only_after_claimed_payload_deletion() -> None:
    repository = InMemoryImportJobRepository()
    service = _service(repository)
    current = datetime.now(UTC)
    job, _ = service.create(
        FakeConnection(), _request(), now=current - timedelta(hours=24)
    )

    claim = service.claim_next(
        {"workerId": "worker-1", "supportedTasks": ["CLEANUP"]}, now=current
    )
    assert claim is not None
    assert claim.cleanup_reason == "EXPIRED"
    assert repository.get(job.import_id).state is ImportState.UPLOADING

    with pytest.raises(ImportStateConflict, match="cleanup"):
        service.reissue_upload_capability(
            job.import_id,
            FakeConnection(),
            expected_state_version=claim.state_version,
        )
    with pytest.raises(ImportClaimConflict, match="cleanup"):
        service.record_sip_stored(
            job.import_id,
            {
                "eventId": str(uuid4()),
                "storedAt": current.isoformat(),
                "sizeBytes": job.declared_compressed_size_bytes,
                "sha256": "a" * 64,
                "uploadRequestId": str(uuid4()),
            },
        )

    payload = _cleanup_payload(claim, current)
    expired = service.record_cleanup_result(job.import_id, payload, now=current)
    replay = service.record_cleanup_result(job.import_id, payload, now=current)

    assert expired == replay
    assert expired.state is ImportState.EXPIRED
    assert expired.quota_reserved_bytes == 0
    assert expired.cleanup_pending is False
    assert expired.active_claim_id is None


def test_ready_expiry_is_claimed_at_its_exact_deadline() -> None:
    repository = InMemoryImportJobRepository()
    service = _service(repository)
    current = datetime.now(UTC)
    uploading, _ = service.create(FakeConnection(), _request(), now=current)
    validating = uploading.transition(
        ImportState.VALIDATING, expected_state_version=0, now=current
    )
    ready = validating.transition(
        ImportState.READY,
        expected_state_version=1,
        now=current,
        expires_at=current,
    )
    repository.replace(ready, expected_state_version=0)

    claim = service.claim_next(
        {"workerId": "worker-1", "supportedTasks": ["CLEANUP"]}, now=current
    )

    assert claim is not None
    assert claim.cleanup_reason == "EXPIRED"


def test_cleanup_never_claims_importing_and_imported_cleanup_keeps_quota() -> None:
    current = datetime.now(UTC)
    repository = InMemoryImportJobRepository()
    service = _service(repository)
    uploading, _ = service.create(FakeConnection(), _request(), now=current)
    validating = uploading.transition(
        ImportState.VALIDATING, expected_state_version=0, now=current
    )
    ready = validating.transition(
        ImportState.READY,
        expected_state_version=1,
        now=current,
        expires_at=current + timedelta(days=7),
        quota_reserved_bytes=123,
    )
    importing = ready.transition(
        ImportState.IMPORTING,
        expected_state_version=2,
        now=current,
        cleanup_pending=True,
    )
    repository.replace(importing, expected_state_version=0)

    assert (
        service.claim_next(
            {"workerId": "worker-1", "supportedTasks": ["CLEANUP"]}, now=current
        )
        is None
    )

    imported = importing.transition(
        ImportState.IMPORTED,
        expected_state_version=3,
        now=current,
        cleanup_pending=True,
    )
    repository.replace(imported, expected_state_version=3)
    claim = service.claim_next(
        {"workerId": "worker-1", "supportedTasks": ["CLEANUP"]}, now=current
    )
    assert claim is not None and claim.cleanup_reason == "IMPORTED"

    cleaned = service.record_cleanup_result(
        imported.import_id, _cleanup_payload(claim, current), now=current
    )
    assert cleaned.state is ImportState.IMPORTED
    assert cleaned.quota_reserved_bytes == 123
    assert cleaned.cleanup_pending is False


def test_notification_reconciliation_is_bounded_and_backed_off() -> None:
    repository = InMemoryImportJobRepository()
    service = _service(repository)
    current = datetime.now(UTC)
    job, _ = service.create(FakeConnection(), _request(), now=current)
    pending = replace(
        job,
        notification_status=NotificationStatus.PENDING,
        notification_for_state=ImportState.READY,
    )
    repository.replace(pending, expected_state_version=0)

    assert service.next_notification_retry(now=current) == pending
    first_failure = service.record_notification_result(
        job.import_id, success=False, error="smtp", now=current
    )
    assert first_failure.notification_attempts == 1
    assert service.next_notification_retry(now=current + timedelta(minutes=4)) is None
    assert (
        service.next_notification_retry(now=current + timedelta(minutes=5))
        == first_failure
    )

    service.record_notification_result(
        job.import_id,
        success=False,
        error="smtp",
        now=current + timedelta(minutes=5),
    )
    service.record_notification_result(
        job.import_id,
        success=False,
        error="smtp",
        now=current + timedelta(minutes=10),
    )
    assert service.next_notification_retry(now=current + timedelta(days=1)) is None


def test_complete_happy_lifecycle_reaches_imported_cleanup_with_audit_evidence() -> (
    None
):
    """Exercise the complete API-owned lifecycle used by media and UI clients."""

    repository = InMemoryImportJobRepository()
    service = _service(repository)
    connection = FakeConnection()
    started = datetime.now(UTC)
    job, _ = service.create(connection, _request(size=1_000_000), now=started)
    states = [job.state]

    validating = service.record_sip_stored(
        job.import_id,
        {
            "eventId": str(uuid4()),
            "storedAt": (started + timedelta(seconds=1)).isoformat(),
            "sizeBytes": 1_000_000,
            "sha256": "a" * 64,
            "uploadRequestId": str(uuid4()),
        },
    )
    states.append(validating.state)
    validation_claim = service.claim_next(
        {"workerId": "worker-1", "supportedTasks": ["VALIDATE"]},
        now=started + timedelta(seconds=2),
    )
    assert validation_claim is not None
    completed = started + timedelta(seconds=3)
    ready = service.record_validation_result(
        job.import_id,
        {
            "eventId": str(uuid4()),
            "claimId": validation_claim.claim_id,
            "expectedStateVersion": validation_claim.state_version,
            "outcome": "READY",
            "completedAt": completed.isoformat(),
            "temporaryPayloadDeleted": False,
            "manifestSha256": "b" * 64,
            "reportSha256": "c" * 64,
            "summary": {
                "entriesObserved": 1,
                "inventoryComplete": True,
                "files": 1,
                "directories": 0,
                "importableFiles": 1,
                "importableDirectories": 0,
                "ignoredEntries": 0,
                "rejectedEntries": 0,
                "warningCount": 0,
                "errorCount": 0,
                "compressedBytes": 1_000_000,
                "extractedBytes": 5_000_000,
                "maxDepth": 0,
            },
        },
        now=completed,
    )
    states.append(ready.state)
    importing = service.confirm(
        job.import_id,
        connection,
        expected_state_version=ready.state_version,
        now=started + timedelta(seconds=4),
    )
    states.append(importing.state)
    import_claim = service.claim_next(
        {"workerId": "worker-1", "supportedTasks": ["IMPORT"]},
        now=started + timedelta(seconds=5),
    )
    assert import_claim is not None
    asset_id = str(uuid5(UUID(job.import_id), "entry:0"))
    imported, event_id, resources = service.commit_import(
        job.import_id,
        {
            "eventId": str(uuid4()),
            "claimId": import_claim.claim_id,
            "expectedStateVersion": import_claim.state_version,
            "manifestSha256": "b" * 64,
            "folders": [],
            "media": [
                {
                    "entryIndex": 0,
                    "relativePath": "notes.txt",
                    "parentRelativePath": "",
                    "assetId": asset_id,
                    "checksumSha256": "d" * 64,
                    "originalName": "notes.txt",
                    "originalMimeType": "text/plain",
                    "dctermsType": "dcmitype:Text",
                    "protocol": "http",
                    "derivativeName": "document.txt",
                    "storagePath": "fasnacht/document",
                }
            ],
        },
        now=started + timedelta(seconds=6),
    )
    states.append(imported.state)
    cleanup_claim = service.claim_next(
        {"workerId": "worker-1", "supportedTasks": ["CLEANUP"]},
        now=started + timedelta(seconds=7),
    )
    assert cleanup_claim is not None
    cleaned = service.record_cleanup_result(
        job.import_id,
        _cleanup_payload(cleanup_claim, started + timedelta(seconds=8)),
        now=started + timedelta(seconds=8),
    )

    assert states == [
        ImportState.UPLOADING,
        ImportState.VALIDATING,
        ImportState.READY,
        ImportState.IMPORTING,
        ImportState.IMPORTED,
    ]
    assert cleaned.state is ImportState.IMPORTED
    assert cleaned.cleanup_pending is False
    assert cleaned.quota_reserved_bytes == 5_000_000
    assert cleaned.validation_event_id is not None
    assert cleaned.import_event_id == event_id
    assert cleaned.cleanup_event_id is not None
    assert resources[0]["assetId"] == asset_id
