"""Internal application service for media-local ZIP export workers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import rfc8785

from .domain import (
    MAX_EXPORT_BYTES,
    ExportClaim,
    ExportJob,
    ExportNotificationStatus,
    ExportProgress,
    ExportState,
    ExportTask,
)
from .manifest import ExportManifest
from .settings import ExportOperatingPolicy
from .repository import (
    ExportJobRepository,
    ExportRepositoryConflict,
)

WORKER_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FAILURE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
DEFAULT_LEASE_SECONDS = 300
MAX_CLOCK_SKEW = timedelta(minutes=5)
NOTIFICATION_RETRY_AFTER = timedelta(minutes=5)


class ExportWorkerValidationError(ValueError):
    """Raised when an internal worker request violates its closed contract."""


class ExportClaimConflict(ValueError):
    """Raised when a worker claim is stale, expired, or owned elsewhere."""


class ExportEventConflict(ValueError):
    """Raised when a result conflicts with accepted immutable evidence."""


class ExportWorkerService:
    """Coordinate durable claims, immutable manifests, and worker results."""

    def __init__(
        self,
        repository: ExportJobRepository,
        *,
        operating_policy: ExportOperatingPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._policy = operating_policy or ExportOperatingPolicy.from_environment()

    def claim_next(
        self, data: Any, *, now: datetime | None = None
    ) -> ExportClaim | None:
        """Atomically lease the oldest eligible supported export task."""

        worker_id, tasks, lease_seconds = _validate_claim_request(data)
        claimed_at = now or datetime.now(UTC)
        self._repository.expire_next_ready(now=claimed_at)
        self._repository.purge_expired_audits(now=claimed_at)
        job = self._repository.claim_next(
            worker_id=worker_id,
            supported_tasks=tasks,
            claim_id=str(uuid4()),
            claimed_at=claimed_at,
            lease_expires_at=claimed_at + timedelta(seconds=lease_seconds),
        )
        return _claim_from_job(job) if job is not None else None

    def heartbeat_claim(
        self,
        claim_id: str,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> tuple[str, datetime]:
        """Renew one worker-owned active lease without changing stateVersion."""

        identifier = _canonical_uuid(claim_id, "claimId")
        worker_id, expected_version = _validate_heartbeat(data)
        current_time = now or datetime.now(UTC)
        job = self._repository.get_by_claim(identifier)
        if (
            job.active_claim_worker_id != worker_id
            or job.state_version != expected_version
            or job.active_claimed_at is None
            or job.active_claim_lease_expires_at is None
            or job.active_claim_lease_seconds is None
            or job.active_claim_lease_expires_at <= current_time
        ):
            raise ExportClaimConflict(
                "The export claim is stale, expired, or not owned by this worker."
            )
        renewed_until = current_time + timedelta(seconds=job.active_claim_lease_seconds)
        renewed = replace(job, active_claim_lease_expires_at=renewed_until)
        self._repository.renew_claim(job, renewed)
        return identifier, renewed_until

    def manifest_for_claim(
        self,
        export_id: str,
        claim_id: str,
        *,
        now: datetime | None = None,
    ) -> ExportManifest:
        """Return the immutable manifest only for its current BUILD claim."""

        export_identifier = _canonical_uuid(export_id, "exportId")
        claim_identifier = _canonical_uuid(claim_id, "claimId")
        job = self._repository.get_by_claim(claim_identifier)
        _require_active_claim(job, ExportTask.BUILD, now or datetime.now(UTC))
        if job.export_id != export_identifier:
            raise ExportClaimConflict("The claim does not belong to this export.")
        manifest = self._repository.get_manifest(export_identifier)
        manifest.validate_identity_for_job(job)
        return manifest

    def record_build_result(
        self,
        export_id: str,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> ExportJob:
        """Publish an idempotent READY or FAILED result for one BUILD claim."""

        export_identifier = _canonical_uuid(export_id, "exportId")
        event, digest = _validate_build_result(data)
        job = self._repository.get(export_identifier)
        if job.build_event_id is not None:
            if (
                job.build_event_id == event["eventId"]
                and job.build_result_digest == digest
            ):
                return job
            raise ExportEventConflict(
                "The build result conflicts with the accepted result."
            )

        current_time = now or datetime.now(UTC)
        _require_result_claim(job, event, ExportTask.BUILD, current_time)
        if event["manifestSha256"] != job.manifest_sha256:
            raise ExportEventConflict(
                "The build result manifest digest is inconsistent."
            )
        _validate_completion_time(job, event["completedAt"], current_time)

        outcome = ExportState(event["outcome"])
        common = {
            "active_claim_id": None,
            "active_claim_task": None,
            "active_claim_worker_id": None,
            "active_claimed_at": None,
            "active_claim_lease_expires_at": None,
            "active_claim_lease_seconds": None,
            "build_event_id": event["eventId"],
            "build_result_digest": digest,
            "notification_status": ExportNotificationStatus.PENDING,
            "notification_for_state": outcome,
            "notification_attempts": 0,
            "notification_sent_at": None,
            "notification_last_attempt_at": None,
            "notification_last_error": None,
        }
        if outcome is ExportState.READY:
            updated = job.transition(
                ExportState.READY,
                expected_state_version=event["expectedStateVersion"],
                now=event["completedAt"],
                ready_at=event["completedAt"],
                expires_at=event["completedAt"]
                + timedelta(hours=self._policy.ready_retention_hours),
                archive_size_bytes=event["archiveSizeBytes"],
                archive_sha256=event["archiveSha256"],
                progress=ExportProgress(
                    files_done=job.progress.files_total,
                    files_total=job.progress.files_total,
                    bytes_done=job.progress.bytes_total,
                    bytes_total=job.progress.bytes_total,
                ),
                **common,
            )
        else:
            updated = job.transition(
                ExportState.FAILED,
                expected_state_version=event["expectedStateVersion"],
                now=event["completedAt"],
                failure_code=event["failureCode"],
                **common,
            )
        try:
            self._repository.save(updated, expected_previous_version=job.state_version)
        except ExportRepositoryConflict:
            accepted = self._repository.get(export_identifier)
            if (
                accepted.build_event_id == event["eventId"]
                and accepted.build_result_digest == digest
            ):
                return accepted
            raise
        return updated

    def record_notification_result(
        self,
        export_id: str,
        *,
        success: bool,
        error: str | None = None,
        now: datetime | None = None,
    ) -> ExportJob:
        """Persist mail submission evidence without changing lifecycle version."""

        identifier = _canonical_uuid(export_id, "exportId")
        job = self._repository.get(identifier)
        if job.notification_status is ExportNotificationStatus.SENT:
            return job
        if job.notification_status not in {
            ExportNotificationStatus.PENDING,
            ExportNotificationStatus.FAILED,
        }:
            raise ExportEventConflict("No export notification is pending.")
        if job.notification_attempts >= 3:
            return job
        current = now or datetime.now(UTC)
        updated = replace(
            job,
            notification_status=(
                ExportNotificationStatus.SENT
                if success
                else ExportNotificationStatus.FAILED
            ),
            notification_attempts=job.notification_attempts + 1,
            notification_sent_at=current if success else None,
            notification_last_attempt_at=current,
            notification_last_error=(None if success else _bounded_error(error)),
        )
        self._repository.update_notification(job, updated)
        return updated

    def next_notification_retry(
        self, *, now: datetime | None = None
    ) -> ExportJob | None:
        """Return at most one due API-owned mail retry candidate."""

        return self._repository.next_notification_retry(
            now=now or datetime.now(UTC), retry_after=NOTIFICATION_RETRY_AFTER
        )

    def record_cleanup_result(
        self,
        export_id: str,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> ExportJob:
        """Accept idempotent deletion proof and purge the frozen manifest."""

        export_identifier = _canonical_uuid(export_id, "exportId")
        event, digest = _validate_cleanup_result(data)
        job = self._repository.get(export_identifier)
        if job.cleanup_event_id is not None:
            if (
                job.cleanup_event_id == event["eventId"]
                and job.cleanup_result_digest == digest
            ):
                return job
            raise ExportEventConflict(
                "The cleanup result conflicts with the accepted result."
            )

        current_time = now or datetime.now(UTC)
        _require_result_claim(job, event, ExportTask.CLEANUP, current_time)
        _validate_completion_time(job, event["completedAt"], current_time)
        updated = job.transition(
            ExportState.DELETED,
            expected_state_version=event["expectedStateVersion"],
            now=event["completedAt"],
            deleted_at=event["completedAt"],
            audit_delete_at=event["completedAt"]
            + timedelta(days=self._policy.audit_retention_days),
            manifest_sha256=None,
            archive_size_bytes=None,
            archive_sha256=None,
            selection=replace(
                job.selection,
                selection_iri=None,
                display_name="Deleted export",
                display_path="Deleted export",
            ),
            active_claim_id=None,
            active_claim_task=None,
            active_claim_worker_id=None,
            active_claimed_at=None,
            active_claim_lease_expires_at=None,
            active_claim_lease_seconds=None,
            cleanup_reason=None,
            cleanup_event_id=event["eventId"],
            cleanup_result_digest=digest,
        )
        try:
            self._repository.complete_cleanup(job, updated)
        except ExportRepositoryConflict:
            accepted = self._repository.get(export_identifier)
            if (
                accepted.cleanup_event_id == event["eventId"]
                and accepted.cleanup_result_digest == digest
            ):
                return accepted
            raise
        return updated


def _validate_claim_request(
    value: Any,
) -> tuple[str, tuple[ExportTask, ...], int]:
    required = {"workerId", "supportedTasks"}
    allowed = required | {"requestedLeaseSeconds"}
    if (
        not isinstance(value, dict)
        or not required <= set(value)
        or not set(value) <= allowed
    ):
        raise ExportWorkerValidationError(
            "The export claim request fields are invalid."
        )
    worker_id = value["workerId"]
    if not isinstance(worker_id, str) or WORKER_ID_RE.fullmatch(worker_id) is None:
        raise ExportWorkerValidationError("workerId is invalid.")
    raw_tasks = value["supportedTasks"]
    if (
        not isinstance(raw_tasks, list)
        or not raw_tasks
        or len(raw_tasks) != len(set(raw_tasks))
    ):
        raise ExportWorkerValidationError(
            "supportedTasks must be non-empty and unique."
        )
    try:
        tasks = tuple(ExportTask(item) for item in raw_tasks)
    except (TypeError, ValueError) as error:
        raise ExportWorkerValidationError(
            "supportedTasks contains an invalid task."
        ) from error
    lease_seconds = value.get("requestedLeaseSeconds", DEFAULT_LEASE_SECONDS)
    if (
        isinstance(lease_seconds, bool)
        or not isinstance(lease_seconds, int)
        or not 60 <= lease_seconds <= 900
    ):
        raise ExportWorkerValidationError(
            "requestedLeaseSeconds must be between 60 and 900."
        )
    return worker_id, tasks, lease_seconds


def _validate_heartbeat(value: Any) -> tuple[str, int]:
    if not isinstance(value, dict) or set(value) != {
        "workerId",
        "expectedStateVersion",
    }:
        raise ExportWorkerValidationError("The heartbeat fields are invalid.")
    worker_id = value["workerId"]
    version = value["expectedStateVersion"]
    if not isinstance(worker_id, str) or WORKER_ID_RE.fullmatch(worker_id) is None:
        raise ExportWorkerValidationError("workerId is invalid.")
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise ExportWorkerValidationError("expectedStateVersion is invalid.")
    return worker_id, version


def _validate_build_result(value: Any) -> tuple[dict[str, Any], str]:
    common = {
        "eventId",
        "claimId",
        "expectedStateVersion",
        "manifestSha256",
        "outcome",
        "completedAt",
        "partialArtifactsDeleted",
    }
    if not isinstance(value, dict) or value.get("outcome") not in {"READY", "FAILED"}:
        raise ExportWorkerValidationError("The build result outcome is invalid.")
    required = (
        common | {"archiveSizeBytes", "archiveSha256", "artifactFinalized"}
        if value["outcome"] == "READY"
        else common | {"failureCode"}
    )
    if set(value) != required:
        raise ExportWorkerValidationError("The build result fields are invalid.")
    normalized = _normalize_common_result(value)
    if value["partialArtifactsDeleted"] is not True:
        raise ExportWorkerValidationError("partialArtifactsDeleted must be true.")
    if value["outcome"] == "READY":
        size = value["archiveSizeBytes"]
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or not 1 <= size <= MAX_EXPORT_BYTES
        ):
            raise ExportWorkerValidationError("archiveSizeBytes is invalid.")
        if value["artifactFinalized"] is not True:
            raise ExportWorkerValidationError("artifactFinalized must be true.")
        normalized["archiveSizeBytes"] = size
        normalized["archiveSha256"] = _sha256(value["archiveSha256"], "archiveSha256")
        normalized["artifactFinalized"] = True
    else:
        failure_code = value["failureCode"]
        if (
            not isinstance(failure_code, str)
            or FAILURE_CODE_RE.fullmatch(failure_code) is None
        ):
            raise ExportWorkerValidationError("failureCode is invalid.")
        normalized["failureCode"] = failure_code
    normalized["partialArtifactsDeleted"] = True
    return normalized, _event_digest(normalized)


def _validate_cleanup_result(value: Any) -> tuple[dict[str, Any], str]:
    required = {
        "eventId",
        "claimId",
        "expectedStateVersion",
        "completedAt",
        "artifactDeleted",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ExportWorkerValidationError("The cleanup result fields are invalid.")
    if value["artifactDeleted"] is not True:
        raise ExportWorkerValidationError("artifactDeleted must be true.")
    normalized = _normalize_common_result(value, manifest=False, outcome=False)
    normalized["artifactDeleted"] = True
    return normalized, _event_digest(normalized)


def _normalize_common_result(
    value: dict[str, Any], *, manifest: bool = True, outcome: bool = True
) -> dict[str, Any]:
    version = value["expectedStateVersion"]
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise ExportWorkerValidationError("expectedStateVersion is invalid.")
    completed = _parse_datetime(value["completedAt"], "completedAt")
    normalized: dict[str, Any] = {
        "eventId": _canonical_uuid(value["eventId"], "eventId"),
        "claimId": _canonical_uuid(value["claimId"], "claimId"),
        "expectedStateVersion": version,
        "completedAt": completed,
    }
    if manifest:
        normalized["manifestSha256"] = _sha256(
            value["manifestSha256"], "manifestSha256"
        )
    if outcome:
        normalized["outcome"] = value["outcome"]
    return normalized


def _require_active_claim(job: ExportJob, task: ExportTask, now: datetime) -> None:
    if (
        job.active_claim_id is None
        or job.active_claim_task is not task
        or job.active_claim_lease_expires_at is None
        or job.active_claim_lease_expires_at <= now
    ):
        raise ExportClaimConflict(f"A current {task.value} claim is required.")


def _require_result_claim(
    job: ExportJob, event: dict[str, Any], task: ExportTask, now: datetime
) -> None:
    _require_active_claim(job, task, now)
    if job.active_claim_id != event["claimId"]:
        raise ExportClaimConflict("The result claim does not match the active claim.")
    if job.state_version != event["expectedStateVersion"]:
        raise ExportClaimConflict("The result uses a stale state version.")


def _validate_completion_time(
    job: ExportJob, completed: datetime, now: datetime
) -> None:
    if completed > now + MAX_CLOCK_SKEW:
        raise ExportEventConflict("The completion time is unreasonably in the future.")
    if job.active_claimed_at is None or completed < job.active_claimed_at:
        raise ExportEventConflict("The task cannot complete before it was claimed.")
    if (
        job.active_claim_lease_expires_at is not None
        and completed > job.active_claim_lease_expires_at
    ):
        raise ExportEventConflict("The task cannot complete after its lease expired.")


def _claim_from_job(job: ExportJob) -> ExportClaim:
    if (
        job.active_claim_id is None
        or job.active_claim_task is None
        or job.active_claimed_at is None
        or job.active_claim_lease_expires_at is None
    ):
        raise RuntimeError("Repository returned an export without a complete claim.")
    return ExportClaim(
        claim_id=job.active_claim_id,
        export_id=job.export_id,
        task=job.active_claim_task,
        state_version=job.state_version,
        claimed_at=job.active_claimed_at,
        lease_expires_at=job.active_claim_lease_expires_at,
        manifest_sha256=(
            job.manifest_sha256 if job.active_claim_task is ExportTask.BUILD else None
        ),
        cleanup_reason=(
            job.cleanup_reason if job.active_claim_task is ExportTask.CLEANUP else None
        ),
    )


def _event_digest(value: dict[str, Any]) -> str:
    serializable = {
        key: (
            item.astimezone(UTC).isoformat().replace("+00:00", "Z")
            if isinstance(item, datetime)
            else item
        )
        for key, item in value.items()
    }
    return hashlib.sha256(rfc8785.dumps(serializable)).hexdigest()


def _canonical_uuid(value: Any, field: str) -> str:
    try:
        parsed = UUID(str(value))
    except (TypeError, ValueError, AttributeError) as error:
        raise ExportWorkerValidationError(
            f"{field} must be a canonical UUID."
        ) from error
    canonical = str(parsed)
    if value != canonical:
        raise ExportWorkerValidationError(f"{field} must be a canonical UUID.")
    return canonical


def _parse_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ExportWorkerValidationError(f"{field} must be an RFC 3339 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ExportWorkerValidationError(
            f"{field} must be an RFC 3339 timestamp."
        ) from error
    if parsed.tzinfo is None:
        raise ExportWorkerValidationError(f"{field} must include a timezone.")
    return parsed.astimezone(UTC)


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ExportWorkerValidationError(f"{field} must be lower-case SHA-256.")
    return value


def _bounded_error(value: str | None) -> str:
    """Return a privacy-neutral bounded delivery error category."""

    normalized = (value or "delivery-error").strip()
    return normalized[:128] or "delivery-error"
