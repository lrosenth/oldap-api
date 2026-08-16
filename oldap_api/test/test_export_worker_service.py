"""Worker lifecycle tests for project-neutral ZIP exports."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from oldap_api.exports.domain import (
    AUDIT_RETENTION_DAYS,
    ExportNotificationStatus,
    ExportState,
)
from oldap_api.exports.repository import (
    ExportNotFoundError,
    InMemoryExportJobRepository,
)
from oldap_api.exports.service import ExportJobService
from oldap_api.exports.settings import ExportOperatingPolicy
from oldap_api.exports.worker_service import (
    ExportClaimConflict,
    ExportEventConflict,
    ExportWorkerService,
    ExportWorkerValidationError,
)
from oldap_api.test.test_export_manifest import bound_job

NOW = datetime(2026, 8, 14, 13, 0, tzinfo=UTC)
WORKER = "media-export-1"


def _service(
    policy: ExportOperatingPolicy | None = None,
) -> tuple[ExportWorkerService, InMemoryExportJobRepository]:
    repository = InMemoryExportJobRepository()
    job, manifest = bound_job()
    repository.create_with_manifest(job, manifest)
    return ExportWorkerService(repository, operating_policy=policy), repository


def test_configured_retention_controls_ready_and_audit_windows():
    policy = ExportOperatingPolicy(
        max_archive_bytes=50_000_000_000,
        ready_retention_hours=48,
        audit_retention_days=90,
    )
    service, _ = _service(policy)
    claim = _claim_build(service)
    ready = service.record_build_result(
        claim.export_id, _ready_result(claim), now=NOW + timedelta(minutes=2)
    )

    assert ready.expires_at == NOW + timedelta(hours=48, minutes=2)


def _claim_build(service: ExportWorkerService):
    claim = service.claim_next(
        {
            "workerId": WORKER,
            "supportedTasks": ["BUILD"],
            "requestedLeaseSeconds": 300,
        },
        now=NOW,
    )
    assert claim is not None
    return claim


def _ready_result(claim) -> dict:
    return {
        "eventId": "55555555-5555-4555-8555-555555555555",
        "claimId": claim.claim_id,
        "expectedStateVersion": claim.state_version,
        "manifestSha256": claim.manifest_sha256,
        "outcome": "READY",
        "completedAt": "2026-08-14T13:02:00Z",
        "archiveSizeBytes": 10_000,
        "archiveSha256": "b" * 64,
        "artifactFinalized": True,
        "partialArtifactsDeleted": True,
    }


def test_build_claim_heartbeat_and_manifest_are_bound_to_current_lease():
    service, repository = _service()
    claim = _claim_build(service)

    building = repository.get(claim.export_id)
    assert building.state is ExportState.BUILDING
    assert building.state_version == 1
    assert (
        service.manifest_for_claim(
            claim.export_id, claim.claim_id, now=NOW + timedelta(seconds=1)
        ).sha256
        == claim.manifest_sha256
    )

    accepted_id, renewed_until = service.heartbeat_claim(
        claim.claim_id,
        {"workerId": WORKER, "expectedStateVersion": claim.state_version},
        now=NOW + timedelta(minutes=1),
    )
    assert accepted_id == claim.claim_id
    assert renewed_until == NOW + timedelta(minutes=6)
    assert repository.get(claim.export_id).state_version == claim.state_version


def test_ready_result_is_idempotent_and_sets_retention_and_progress():
    service, _ = _service()
    claim = _claim_build(service)
    event = _ready_result(claim)

    ready = service.record_build_result(
        claim.export_id, event, now=NOW + timedelta(minutes=2)
    )
    replay = service.record_build_result(
        claim.export_id, event, now=NOW + timedelta(minutes=3)
    )

    assert replay == ready
    assert ready.state is ExportState.READY
    assert ready.archive_sha256 == "b" * 64
    assert ready.expires_at == NOW + timedelta(hours=24, minutes=2)
    assert ready.progress.files_done == ready.progress.files_total == 2
    assert ready.active_claim_id is None
    assert ready.notification_status is ExportNotificationStatus.PENDING
    assert ready.notification_for_state is ExportState.READY

    conflicting = event | {"archiveSha256": "c" * 64}
    with pytest.raises(ExportEventConflict):
        service.record_build_result(claim.export_id, conflicting, now=NOW)


def test_failed_result_requires_complete_cleanup_before_deleted_audit_hull():
    service, repository = _service()
    claim = _claim_build(service)
    failed_event = {
        "eventId": "66666666-6666-4666-8666-666666666666",
        "claimId": claim.claim_id,
        "expectedStateVersion": claim.state_version,
        "manifestSha256": claim.manifest_sha256,
        "outcome": "FAILED",
        "completedAt": "2026-08-14T13:02:00Z",
        "failureCode": "SOURCE_MISSING",
        "partialArtifactsDeleted": True,
    }
    failed = service.record_build_result(
        claim.export_id, failed_event, now=NOW + timedelta(minutes=2)
    )
    assert failed.state is ExportState.FAILED

    cleanup = service.claim_next(
        {"workerId": WORKER, "supportedTasks": ["CLEANUP"]},
        now=NOW + timedelta(minutes=3),
    )
    assert cleanup is not None
    assert cleanup.cleanup_reason == "FAILED"
    completed_at = NOW + timedelta(minutes=4)
    cleanup_event = {
        "eventId": "77777777-7777-4777-8777-777777777777",
        "claimId": cleanup.claim_id,
        "expectedStateVersion": cleanup.state_version,
        "completedAt": completed_at.isoformat().replace("+00:00", "Z"),
        "artifactDeleted": True,
    }
    deleted = service.record_cleanup_result(
        cleanup.export_id, cleanup_event, now=completed_at
    )

    assert deleted.state is ExportState.DELETED
    assert deleted.manifest_sha256 is None
    assert deleted.selection.selection_iri is None
    assert deleted.selection.display_path == "Deleted export"
    assert deleted.audit_delete_at == completed_at + timedelta(
        days=AUDIT_RETENTION_DAYS
    )
    assert (
        service.record_cleanup_result(
            cleanup.export_id, cleanup_event, now=completed_at
        )
        == deleted
    )
    with pytest.raises(ExportNotFoundError):
        repository.get_manifest(cleanup.export_id)


def test_public_cancellation_invalidates_build_claim_and_queues_cleanup_later():
    service, repository = _service()
    claim = _claim_build(service)
    connection = type(
        "Connection",
        (),
        {
            "userIri": "https://example.org/users/alice",
            "userid": "alice",
        },
    )()
    cancelled = ExportJobService(repository).delete(
        claim.export_id,
        connection,
        expected_state_version=claim.state_version,
        now=NOW + timedelta(minutes=1),
    )
    assert cancelled.state is ExportState.CANCELLED
    assert cancelled.active_claim_id is None
    with pytest.raises(ExportClaimConflict):
        service.record_build_result(
            claim.export_id,
            _ready_result(claim),
            now=NOW + timedelta(minutes=2),
        )


def test_worker_contract_rejects_invalid_claim_and_future_completion():
    service, _ = _service()
    with pytest.raises(ExportWorkerValidationError):
        service.claim_next({"workerId": "bad worker", "supportedTasks": ["BUILD"]})

    claim = _claim_build(service)
    event = _ready_result(claim) | {"completedAt": "2026-08-14T14:00:00Z"}
    with pytest.raises(ExportEventConflict, match="future"):
        service.record_build_result(
            claim.export_id, event, now=NOW + timedelta(minutes=1)
        )


def test_expired_build_claim_is_replaced_and_old_worker_result_is_rejected():
    service, _ = _service()
    first = _claim_build(service)
    second = service.claim_next(
        {"workerId": "media-export-2", "supportedTasks": ["BUILD"]},
        now=NOW + timedelta(minutes=6),
    )

    assert second is not None
    assert second.claim_id != first.claim_id
    assert second.state_version == first.state_version + 1
    with pytest.raises(ExportClaimConflict):
        service.record_build_result(
            first.export_id,
            _ready_result(first) | {"completedAt": "2026-08-14T13:06:30Z"},
            now=NOW + timedelta(minutes=6, seconds=30),
        )


def test_notification_retry_is_bounded_backed_off_and_lifecycle_neutral():
    service, _ = _service()
    claim = _claim_build(service)
    ready = service.record_build_result(
        claim.export_id, _ready_result(claim), now=NOW + timedelta(minutes=2)
    )

    first = service.record_notification_result(
        ready.export_id,
        success=False,
        error="smtp-timeout",
        now=NOW + timedelta(minutes=3),
    )
    assert first.state is ExportState.READY
    assert first.state_version == ready.state_version
    assert first.notification_status is ExportNotificationStatus.FAILED
    assert first.notification_attempts == 1
    assert service.next_notification_retry(now=NOW + timedelta(minutes=7)) is None
    assert service.next_notification_retry(now=NOW + timedelta(minutes=8)) == first

    sent = service.record_notification_result(
        ready.export_id, success=True, now=NOW + timedelta(minutes=8)
    )
    assert sent.notification_status is ExportNotificationStatus.SENT
    assert sent.notification_attempts == 2
    assert service.next_notification_retry(now=NOW + timedelta(days=1)) is None


def test_deleted_ready_export_does_not_retry_stale_download_mail():
    service, repository = _service()
    claim = _claim_build(service)
    ready = service.record_build_result(
        claim.export_id, _ready_result(claim), now=NOW + timedelta(minutes=2)
    )
    failed_mail = service.record_notification_result(
        ready.export_id,
        success=False,
        error="smtp-timeout",
        now=NOW + timedelta(minutes=3),
    )
    deleting = failed_mail.transition(
        ExportState.DELETING,
        expected_state_version=failed_mail.state_version,
        now=NOW + timedelta(minutes=4),
        cleanup_reason="READY_DELETE",
    )
    repository.save(deleting, expected_previous_version=failed_mail.state_version)

    assert service.next_notification_retry(now=NOW + timedelta(minutes=8)) is None


def test_elapsed_ready_is_expired_before_cleanup_claim():
    service, repository = _service()
    claim = _claim_build(service)
    ready = service.record_build_result(
        claim.export_id, _ready_result(claim), now=NOW + timedelta(minutes=2)
    )

    cleanup = service.claim_next(
        {"workerId": WORKER, "supportedTasks": ["CLEANUP"]},
        now=ready.expires_at,
    )

    assert cleanup is not None
    assert cleanup.cleanup_reason == "EXPIRED"
    assert cleanup.state_version == ready.state_version + 2
    assert repository.get(ready.export_id).state is ExportState.DELETING


def test_content_free_audit_hull_is_purged_after_deadline():
    repository = InMemoryExportJobRepository()
    job, _ = bound_job()
    deleted = replace(
        job,
        state=ExportState.DELETED,
        deleted_at=NOW,
        audit_delete_at=NOW + timedelta(days=AUDIT_RETENTION_DAYS),
        manifest_sha256=None,
    )
    repository.create(deleted)
    service = ExportWorkerService(repository)

    assert (
        service.claim_next(
            {"workerId": WORKER, "supportedTasks": ["CLEANUP"]},
            now=deleted.audit_delete_at,
        )
        is None
    )
    with pytest.raises(ExportNotFoundError):
        repository.get(deleted.export_id)
