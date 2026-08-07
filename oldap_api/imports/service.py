"""Application service coordinating import authorization and persistence."""

from __future__ import annotations

import base64
import binascii
import re
import unicodedata
import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from .authorization import (
    ImportAuthorizer,
    ImportTargetInspector,
    ImportTargetNotFoundError,
)
from .capabilities import UploadAuthorization, UploadCapabilityIssuer
from .commit import ImportCommitConflict, validate_import_commit
from .domain import (
    MAX_COMPRESSED_BYTES,
    ImportEventConflict,
    ImportClaim,
    ImportClaimConflict,
    ImportJob,
    ImportState,
    ImportStateConflict,
    ImportTask,
    ImportVersionConflict,
    NotificationStatus,
    conservative_quota_reservation,
)
from .repository import ImportJobRepository, ImportNotFoundError

PROJECT_SHORT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
MAX_CURSOR_LENGTH = 512
NOTIFICATION_RETRY_AFTER = timedelta(minutes=5)


class ImportValidationError(ValueError):
    """Raised when a public request violates the closed input contract."""

    code = "IMPORT_REQUEST_INVALID"


class ImportPayloadTooLargeError(ImportValidationError):
    """Raised when the declared ZIP size exceeds the immutable MVP ceiling."""

    code = "UPLOAD_SIZE_LIMIT"


@dataclass(frozen=True, slots=True)
class SipStoredEvent:
    """Validated immutable receipt emitted by media ingress."""

    event_id: str
    stored_at: datetime
    size_bytes: int
    sha256: str
    upload_request_id: str


@dataclass(frozen=True, slots=True)
class ImportJobPage:
    """One stable cursor page of caller-owned import jobs."""

    items: tuple[ImportJob, ...]
    next_cursor: str | None = None


class ImportJobService:
    """Own public job creation, visibility, and versioned user actions."""

    def __init__(
        self,
        repository: ImportJobRepository,
        authorizer: ImportAuthorizer,
        capability_issuer: UploadCapabilityIssuer,
        target_inspector: ImportTargetInspector | None = None,
    ) -> None:
        self._repository = repository
        self._authorizer = authorizer
        self._capability_issuer = capability_issuer
        self._target_inspector = target_inspector

    def create(
        self,
        connection: Any,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> tuple[ImportJob, UploadAuthorization]:
        """Authorize, reserve quota atomically, persist, and issue upload access."""
        request_data = _validate_create_request(data)
        target = self._authorizer.authorize_target(
            connection,
            project_short_name=request_data["projectShortName"],
            staging_area_iri=request_data["stagingAreaIri"],
            target_root_folder_iri=request_data["targetRootFolderIri"],
        )
        current = now or datetime.now(UTC)
        job = ImportJob(
            import_id=str(uuid4()),
            state=ImportState.UPLOADING,
            state_version=0,
            created_at=current,
            updated_at=current,
            requested_by_iri=str(connection.userIri),
            requested_by_user_id=str(connection.userid),
            target=target.snapshot,
            original_file_name=request_data["originalFileName"],
            declared_compressed_size_bytes=request_data["compressedSizeBytes"],
            quota_reserved_bytes=conservative_quota_reservation(
                request_data["compressedSizeBytes"]
            ),
        )
        upload = self._capability_issuer.issue(job, now=current)
        self._repository.create(job, quota_limit_bytes=target.quota_limit_bytes)
        return job, upload

    def get_for_user(self, import_id: str, connection: Any) -> ImportJob:
        """Return only a job owned by the caller, hiding unauthorized IDs."""
        _validate_uuid(import_id)
        job = self._repository.get(import_id)
        if job.requested_by_iri != str(connection.userIri):
            raise ImportNotFoundError("Import job not found.")
        return job

    def list_for_user(
        self,
        connection: Any,
        *,
        state: ImportState | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> ImportJobPage:
        """List caller-owned jobs through an opaque, stable cursor."""
        if not 1 <= limit <= 100:
            raise ImportValidationError("limit must be between 1 and 100.")
        jobs = self._repository.list_for_owner(str(connection.userIri))
        if state is not None:
            jobs = [job for job in jobs if job.state is state]
        start = 0
        if cursor is not None:
            cursor_key = _decode_cursor(cursor)
            try:
                start = next(
                    index + 1
                    for index, job in enumerate(jobs)
                    if (job.created_at, job.import_id) == cursor_key
                )
            except StopIteration as error:
                raise ImportValidationError(
                    "cursor does not identify a job in this result set."
                ) from error
        selected = jobs[start : start + limit + 1]
        items = tuple(selected[:limit])
        next_cursor = (
            _encode_cursor(items[-1]) if len(selected) > limit and items else None
        )
        return ImportJobPage(items=items, next_cursor=next_cursor)

    def reissue_upload_capability(
        self,
        import_id: str,
        connection: Any,
        *,
        expected_state_version: int,
    ) -> UploadAuthorization:
        """Issue another expiring token only for an unchanged UPLOADING job."""
        job = self.get_for_user(import_id, connection)
        if job.state_version != expected_state_version:
            raise ImportVersionConflict("The import job changed; refresh it first.")
        if job.state is not ImportState.UPLOADING:
            raise ImportStateConflict("Upload capabilities require UPLOADING state.")
        if job.active_claim_id is not None:
            raise ImportStateConflict(
                "Upload capabilities are unavailable while cleanup is active."
            )
        return self._capability_issuer.issue(job)

    def cancel(
        self,
        import_id: str,
        connection: Any,
        *,
        expected_state_version: int,
        now: datetime | None = None,
    ) -> ImportJob:
        """Cancel UPLOADING/READY and release its quota reservation atomically."""
        job = self.get_for_user(import_id, connection)
        updated = job.transition(
            ImportState.CANCELLED,
            expected_state_version=expected_state_version,
            now=now,
            quota_reserved_bytes=0,
            cleanup_pending=True,
            active_claim_id=None,
            active_claim_task=None,
            active_claim_worker_id=None,
            active_claimed_at=None,
            active_claim_lease_expires_at=None,
        )
        self._repository.replace(
            updated,
            expected_state_version=job.state_version,
        )
        return updated

    def confirm(
        self,
        import_id: str,
        connection: Any,
        *,
        expected_state_version: int,
        now: datetime | None = None,
    ) -> ImportJob:
        """Reauthorize an unexpired READY target and atomically request import."""
        job = self.get_for_user(import_id, connection)
        current = now or datetime.now(UTC)
        if job.expires_at is None or job.expires_at <= current:
            from .domain import ImportStateConflict

            raise ImportStateConflict("The validated import has expired.")
        authorized = self._authorizer.authorize_target(
            connection,
            project_short_name=job.target.project_short_name,
            staging_area_iri=job.target.staging_area_iri,
            target_root_folder_iri=job.target.target_root_folder_iri,
        )
        if authorized.snapshot != job.target:
            from .domain import ImportStateConflict

            raise ImportStateConflict("The selected staging target changed.")
        updated = job.transition(
            ImportState.IMPORTING,
            expected_state_version=expected_state_version,
            now=current,
        )
        self._repository.replace(
            updated,
            expected_state_version=job.state_version,
            quota_limit_bytes=authorized.quota_limit_bytes,
        )
        return updated

    def record_sip_stored(self, import_id: str, data: Any) -> ImportJob:
        """Idempotently accept the durable SIP receipt and queue validation."""
        _validate_uuid(import_id)
        event = _validate_sip_stored_event(data)
        job = self._repository.get(import_id)
        if job.sip_stored_event_id is not None:
            if _sip_receipt_matches(job, event):
                return job
            raise ImportEventConflict(
                "The SIP-stored event conflicts with the accepted receipt."
            )
        if job.active_claim_id is not None:
            raise ImportClaimConflict(
                "The SIP cannot be accepted while cleanup is active."
            )
        if event.size_bytes != job.declared_compressed_size_bytes:
            raise ImportEventConflict(
                "The stored SIP size differs from the declared immutable size."
            )
        updated = job.transition(
            ImportState.VALIDATING,
            expected_state_version=job.state_version,
            now=event.stored_at,
            uploaded_at=event.stored_at,
            actual_compressed_size_bytes=event.size_bytes,
            sip_sha256=event.sha256,
            sip_upload_request_id=event.upload_request_id,
            sip_stored_event_id=event.event_id,
        )
        try:
            self._repository.replace(
                updated,
                expected_state_version=job.state_version,
            )
        except ImportVersionConflict:
            # A concurrent identical notification is still an idempotent replay.
            accepted = self._repository.get(import_id)
            if _sip_receipt_matches(accepted, event):
                return accepted
            raise ImportEventConflict(
                "The SIP-stored event conflicts with a concurrent event."
            )
        return updated

    def claim_next(
        self, data: Any, *, now: datetime | None = None
    ) -> ImportClaim | None:
        """Atomically lease at most one eligible task across all import jobs."""
        worker_id, tasks, lease_seconds = _validate_claim_request(data)
        claimed_at = now or datetime.now(UTC)
        claim_id = str(uuid4())
        job = self._repository.claim_next(
            worker_id=worker_id,
            supported_tasks=tasks,
            claim_id=claim_id,
            claimed_at=claimed_at,
            lease_expires_at=claimed_at + timedelta(seconds=lease_seconds),
        )
        return _claim_from_job(job) if job else None

    def heartbeat_claim(
        self,
        claim_id: str,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> tuple[str, datetime]:
        """Renew an active lease without changing the lifecycle version."""
        claim_id = _canonical_uuid(claim_id, "claimId")
        worker_id, expected_version = _validate_heartbeat(data)
        current = now or datetime.now(UTC)
        job = self._repository.get_by_claim(claim_id)
        if (
            job.active_claim_worker_id != worker_id
            or job.state_version != expected_version
            or job.active_claim_lease_expires_at is None
            or job.active_claim_lease_expires_at <= current
            or job.active_claimed_at is None
        ):
            raise ImportClaimConflict(
                "The worker claim is stale or not owned by this worker."
            )
        lease_duration = job.active_claim_lease_expires_at - job.active_claimed_at
        renewed_until = current + lease_duration
        updated = replace(job, active_claim_lease_expires_at=renewed_until)
        self._repository.replace(
            updated,
            expected_state_version=job.state_version,
        )
        return claim_id, renewed_until

    def preflight_target(
        self,
        claim_id: str,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Compare ZIP root names with the leased job's current target children."""

        claim_id = _canonical_uuid(claim_id, "claimId")
        worker_id, expected_version, candidates = _validate_target_preflight(data)
        current = now or datetime.now(UTC)
        job = self._repository.get_by_claim(claim_id)
        if (
            job.active_claim_worker_id != worker_id
            or job.active_claim_task != ImportTask.VALIDATE.value
            or job.state_version != expected_version
            or job.active_claim_lease_expires_at is None
            or job.active_claim_lease_expires_at <= current
        ):
            raise ImportClaimConflict(
                "A current worker-owned VALIDATE claim is required."
            )
        if self._target_inspector is None:
            raise RuntimeError("Import target inspection is not configured.")
        try:
            inspection = self._target_inspector.inspect_target(job.target)
        except ImportTargetNotFoundError:
            inspection = None
        findings: list[dict[str, Any]] = []
        if inspection is None or inspection.snapshot != job.target:
            findings.append({"code": "TARGET_CHANGED", "blocking": True})
        else:
            children_by_key: dict[str, list[Any]] = {}
            for child in inspection.children:
                children_by_key.setdefault(_portable_name_key(child.name), []).append(
                    child
                )
            for candidate in candidates:
                matches = children_by_key.get(_portable_name_key(candidate["name"]), [])
                if not matches:
                    continue
                folder_conflict = candidate["entryType"] == "directory" or any(
                    child.kind == "folder" for child in matches
                )
                existing = next(
                    (
                        child
                        for child in matches
                        if child.kind == ("folder" if folder_conflict else "media")
                    ),
                    matches[0],
                )
                findings.append(
                    {
                        "entryIndex": candidate["entryIndex"],
                        "code": (
                            "TARGET_FOLDER_COLLISION"
                            if folder_conflict
                            else "TARGET_MEDIA_NAME_COLLISION"
                        ),
                        "blocking": folder_conflict,
                        "existingKind": existing.kind,
                        "existingName": _bounded_utf8(existing.name, 255),
                    }
                )
        return {
            "claimId": claim_id,
            "targetRootFolderIri": job.target.target_root_folder_iri,
            "findings": findings,
        }

    def record_validation_result(
        self,
        import_id: str,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> ImportJob:
        """Idempotently reconcile quota and publish READY, INVALID, or FAILED."""
        _validate_uuid(import_id)
        event, digest = _validate_validation_result(data)
        job = self._repository.get(import_id)
        if job.validation_event_id is not None:
            if (
                job.validation_event_id == event["eventId"]
                and job.validation_result_digest == digest
            ):
                return job
            raise ImportEventConflict(
                "The validation result conflicts with the accepted result."
            )

        server_now = now or datetime.now(UTC)
        if (
            job.active_claim_id != event["claimId"]
            or job.active_claim_task != ImportTask.VALIDATE.value
            or job.active_claim_lease_expires_at is None
            or job.active_claim_lease_expires_at <= server_now
        ):
            raise ImportClaimConflict("A current VALIDATE claim is required.")
        if job.state_version != event["expectedStateVersion"]:
            raise ImportVersionConflict(
                "The validation result uses a stale state version."
            )

        outcome = ImportState(event["outcome"])
        summary = event["summary"]
        extracted_bytes = summary["extractedBytes"]
        if summary["compressedBytes"] != job.actual_compressed_size_bytes:
            raise ImportEventConflict(
                "Validation summary compressed bytes differ from the stored SIP."
            )
        if event["completedAt"] > server_now + timedelta(minutes=5):
            raise ImportEventConflict(
                "Validation completion time is unreasonably in the future."
            )
        if job.uploaded_at and event["completedAt"] < job.uploaded_at:
            raise ImportEventConflict(
                "Validation cannot complete before the SIP was stored."
            )
        if outcome is ImportState.READY and (
            not summary["inventoryComplete"]
            or summary["errorCount"] != 0
            or summary["rejectedEntries"] != 0
        ):
            raise ImportEventConflict(
                "READY requires complete inventory without errors or rejected entries."
            )
        if extracted_bytes > job.quota_reserved_bytes:
            raise ImportEventConflict(
                "Extracted bytes exceed the quota reserved for this ZIP."
            )
        changes: dict[str, Any] = {
            "validation_completed_at": event["completedAt"],
            "extracted_size_bytes": extracted_bytes,
            "quota_reserved_bytes": (
                extracted_bytes if outcome is ImportState.READY else 0
            ),
            "report_available": True,
            "summary": summary,
            "failure_code": event.get("failureCode"),
            "validation_event_id": event["eventId"],
            "validation_result_digest": digest,
            "validation_outcome": outcome,
            "manifest_sha256": event.get("manifestSha256"),
            "report_sha256": event["reportSha256"],
            "active_claim_id": None,
            "active_claim_task": None,
            "active_claim_worker_id": None,
            "active_claimed_at": None,
            "active_claim_lease_expires_at": None,
            "notification_status": NotificationStatus.PENDING,
            "notification_for_state": outcome,
            "notification_attempts": 0,
            "notification_sent_at": None,
            "notification_last_attempt_at": None,
            "notification_last_error": None,
        }
        if outcome is ImportState.READY:
            changes["expires_at"] = event["completedAt"] + timedelta(days=7)
        updated = job.transition(
            outcome,
            expected_state_version=event["expectedStateVersion"],
            now=event["completedAt"],
            **changes,
        )
        try:
            self._repository.replace(
                updated,
                expected_state_version=job.state_version,
            )
        except ImportVersionConflict:
            accepted = self._repository.get(import_id)
            if (
                accepted.validation_event_id == event["eventId"]
                and accepted.validation_result_digest == digest
            ):
                return accepted
            raise ImportEventConflict(
                "The validation result conflicts with a concurrent result."
            )
        return updated

    def record_notification_result(
        self,
        import_id: str,
        *,
        success: bool,
        error: str | None = None,
        now: datetime | None = None,
    ) -> ImportJob:
        """Persist mail submission independently from lifecycle state."""
        job = self._repository.get(import_id)
        if job.notification_status is NotificationStatus.SENT:
            return job
        if job.notification_status not in {
            NotificationStatus.PENDING,
            NotificationStatus.FAILED,
        }:
            raise ImportStateConflict("No import notification is pending.")
        if job.notification_attempts >= 3:
            return job
        attempts = job.notification_attempts + 1
        current = now or datetime.now(UTC)
        updated = replace(
            job,
            notification_status=(
                NotificationStatus.SENT if success else NotificationStatus.FAILED
            ),
            notification_attempts=attempts,
            notification_sent_at=current if success else None,
            notification_last_attempt_at=current,
            notification_last_error=(None if success else _bounded_error(error)),
        )
        self._repository.replace(
            updated,
            expected_state_version=job.state_version,
        )
        return updated

    def next_notification_retry(
        self, *, now: datetime | None = None
    ) -> ImportJob | None:
        """Return at most one API-owned mail retry candidate after backoff."""

        return self._repository.next_notification_retry(
            now=now or datetime.now(UTC), retry_after=NOTIFICATION_RETRY_AFTER
        )

    def commit_import(
        self,
        import_id: str,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> tuple[ImportJob, str, tuple[dict[str, Any], ...]]:
        """Atomically register all staging resources and finish one IMPORT claim.

        The repository repeats target, authorization, and collision checks in
        the same GraphDB transaction that creates resources and changes the job
        to IMPORTED. Identical event replay returns the retained mapping.
        """

        _validate_uuid(import_id)
        job = self._repository.get(import_id)
        try:
            commit = validate_import_commit(
                import_id, data, job.target.project_short_name
            )
        except (TypeError, ValueError) as error:
            raise ImportValidationError(str(error)) from error
        if job.import_event_id is not None:
            if (
                job.import_event_id == commit.event_id
                and job.import_result_digest == commit.digest
            ):
                return (
                    job,
                    commit.event_id,
                    tuple(dict(resource) for resource in job.imported_resources),
                )
            raise ImportCommitConflict(
                "The import commit conflicts with the accepted event."
            )

        current = now or datetime.now(UTC)
        if (
            job.state is not ImportState.IMPORTING
            or job.active_claim_id != commit.claim_id
            or job.active_claim_task != ImportTask.IMPORT.value
            or job.active_claim_lease_expires_at is None
            or job.active_claim_lease_expires_at <= current
        ):
            raise ImportClaimConflict("A current IMPORT claim is required.")
        if job.state_version != commit.expected_state_version:
            raise ImportVersionConflict("The import commit uses a stale state version.")
        if job.manifest_sha256 != commit.manifest_sha256:
            raise ImportEventConflict(
                "The import commit manifest differs from validated evidence."
            )
        resources = commit.resources
        updated = job.transition(
            ImportState.IMPORTED,
            expected_state_version=commit.expected_state_version,
            now=current,
            imported_at=current,
            expires_at=None,
            cleanup_pending=True,
            active_claim_id=None,
            active_claim_task=None,
            active_claim_worker_id=None,
            active_claimed_at=None,
            active_claim_lease_expires_at=None,
            import_event_id=commit.event_id,
            import_result_digest=commit.digest,
            imported_resources=resources,
            notification_status=NotificationStatus.PENDING,
            notification_for_state=ImportState.IMPORTED,
            notification_attempts=0,
            notification_sent_at=None,
            notification_last_attempt_at=None,
            notification_last_error=None,
        )
        try:
            self._repository.commit_import(job, updated, commit)
        except ImportVersionConflict:
            accepted = self._repository.get(import_id)
            if (
                accepted.import_event_id == commit.event_id
                and accepted.import_result_digest == commit.digest
            ):
                return (
                    accepted,
                    commit.event_id,
                    tuple(dict(resource) for resource in accepted.imported_resources),
                )
            raise
        return updated, commit.event_id, resources

    def fail_import(
        self,
        import_id: str,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> ImportJob:
        """Record a compensated terminal IMPORT failure idempotently."""

        _validate_uuid(import_id)
        event, digest = _validate_import_failure(data)
        job = self._repository.get(import_id)
        if job.task_failure_event_id is not None:
            if (
                job.task_failure_event_id == event["eventId"]
                and job.task_failure_digest == digest
            ):
                return job
            raise ImportEventConflict(
                "The task failure conflicts with the accepted event."
            )
        current = now or datetime.now(UTC)
        if (
            job.state is not ImportState.IMPORTING
            or job.active_claim_id != event["claimId"]
            or job.active_claim_task != ImportTask.IMPORT.value
            or job.active_claim_lease_expires_at is None
            or job.active_claim_lease_expires_at <= current
        ):
            raise ImportClaimConflict("A current IMPORT claim is required.")
        if job.state_version != event["expectedStateVersion"]:
            raise ImportVersionConflict("The task failure uses a stale state version.")
        updated = job.transition(
            ImportState.FAILED,
            expected_state_version=event["expectedStateVersion"],
            now=current,
            quota_reserved_bytes=0,
            cleanup_pending=False,
            failure_code=event["failureCode"],
            active_claim_id=None,
            active_claim_task=None,
            active_claim_worker_id=None,
            active_claimed_at=None,
            active_claim_lease_expires_at=None,
            task_failure_event_id=event["eventId"],
            task_failure_digest=digest,
            notification_status=NotificationStatus.PENDING,
            notification_for_state=ImportState.FAILED,
            notification_attempts=0,
            notification_sent_at=None,
            notification_last_attempt_at=None,
            notification_last_error=None,
        )
        try:
            self._repository.replace(updated, expected_state_version=job.state_version)
        except ImportVersionConflict:
            accepted = self._repository.get(import_id)
            if (
                accepted.task_failure_event_id == event["eventId"]
                and accepted.task_failure_digest == digest
            ):
                return accepted
            raise
        return updated

    def record_cleanup_result(
        self,
        import_id: str,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> ImportJob:
        """Accept proof of temporary-payload deletion for one CLEANUP claim.

        Expiry becomes authoritative only here, after the media worker has
        deleted the API-selected payload. Existing terminal states keep their
        lifecycle identity; IMPORTED retains its extracted-byte quota because
        those originals now exist in the staging area.
        """

        _validate_uuid(import_id)
        event, digest = _validate_cleanup_result(data)
        job = self._repository.get(import_id)
        if job.cleanup_event_id is not None:
            if (
                job.cleanup_event_id == event["eventId"]
                and job.cleanup_result_digest == digest
            ):
                return job
            raise ImportEventConflict(
                "The cleanup result conflicts with the accepted result."
            )

        current = now or datetime.now(UTC)
        if event["completedAt"] > current + timedelta(minutes=5):
            raise ImportEventConflict(
                "Cleanup completion time is unreasonably in the future."
            )
        expected_reason = _cleanup_reason(job)
        if (
            job.active_claim_id != event["claimId"]
            or job.active_claim_task != ImportTask.CLEANUP.value
            or job.active_claim_lease_expires_at is None
            or job.active_claim_lease_expires_at <= current
        ):
            raise ImportClaimConflict("A current CLEANUP claim is required.")
        if job.state_version != event["expectedStateVersion"]:
            raise ImportVersionConflict(
                "The cleanup result uses a stale state version."
            )
        if event["reason"] != expected_reason:
            raise ImportEventConflict(
                "The cleanup reason differs from the claimed job."
            )

        common_changes = {
            "updated_at": current,
            "cleanup_pending": False,
            "active_claim_id": None,
            "active_claim_task": None,
            "active_claim_worker_id": None,
            "active_claimed_at": None,
            "active_claim_lease_expires_at": None,
            "cleanup_event_id": event["eventId"],
            "cleanup_result_digest": digest,
        }
        if expected_reason == ImportState.EXPIRED.value:
            updated = job.transition(
                ImportState.EXPIRED,
                expected_state_version=event["expectedStateVersion"],
                now=current,
                quota_reserved_bytes=0,
                cleanup_pending=False,
                active_claim_id=None,
                active_claim_task=None,
                active_claim_worker_id=None,
                active_claimed_at=None,
                active_claim_lease_expires_at=None,
                cleanup_event_id=event["eventId"],
                cleanup_result_digest=digest,
            )
        else:
            updated = replace(
                job,
                state_version=job.state_version + 1,
                **common_changes,
            )
        try:
            self._repository.replace(updated, expected_state_version=job.state_version)
        except ImportVersionConflict:
            accepted = self._repository.get(import_id)
            if (
                accepted.cleanup_event_id == event["eventId"]
                and accepted.cleanup_result_digest == digest
            ):
                return accepted
            raise
        return updated


def _validate_import_failure(value: Any) -> tuple[dict[str, Any], str]:
    required = {
        "eventId",
        "claimId",
        "expectedStateVersion",
        "task",
        "failureCode",
        "compensated",
        "temporaryPayloadDeleted",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ImportValidationError("The task-failure fields are invalid.")
    normalized = dict(value)
    normalized["eventId"] = _canonical_uuid(value["eventId"], "eventId")
    normalized["claimId"] = _canonical_uuid(value["claimId"], "claimId")
    version = value["expectedStateVersion"]
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version < 0
        or value["task"] != "IMPORT"
        or value["compensated"] is not True
        or value["temporaryPayloadDeleted"] is not True
        or not isinstance(value["failureCode"], str)
        or re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", value["failureCode"]) is None
    ):
        raise ImportValidationError("The IMPORT failure evidence is invalid.")
    digest = hashlib.sha256(
        json.dumps(
            normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return normalized, digest


def _validate_cleanup_result(value: Any) -> tuple[dict[str, Any], str]:
    """Validate the closed, idempotent cleanup proof contract."""

    required = {
        "eventId",
        "claimId",
        "expectedStateVersion",
        "reason",
        "temporaryPayloadDeleted",
        "completedAt",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ImportValidationError("The cleanup-result fields are invalid.")
    normalized = dict(value)
    normalized["eventId"] = _canonical_uuid(value["eventId"], "eventId")
    normalized["claimId"] = _canonical_uuid(value["claimId"], "claimId")
    try:
        completed_at = datetime.fromisoformat(
            str(value["completedAt"]).replace("Z", "+00:00")
        )
    except ValueError as error:
        raise ImportValidationError(
            "completedAt must be an ISO 8601 date-time."
        ) from error
    if completed_at.tzinfo is None:
        raise ImportValidationError("completedAt must include a timezone.")
    normalized["completedAt"] = completed_at.astimezone(UTC)
    version = value["expectedStateVersion"]
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version < 0
        or value["reason"] not in {"CANCELLED", "EXPIRED", "IMPORTED", "FAILED"}
        or value["temporaryPayloadDeleted"] is not True
    ):
        raise ImportValidationError("The cleanup-result evidence is invalid.")
    digest_value = normalized | {
        "completedAt": normalized["completedAt"].isoformat().replace("+00:00", "Z")
    }
    digest = hashlib.sha256(
        json.dumps(
            digest_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return normalized, digest


def _validate_create_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ImportValidationError("A JSON object is required.")
    required = {
        "projectShortName",
        "stagingAreaIri",
        "targetRootFolderIri",
        "originalFileName",
        "compressedSizeBytes",
    }
    if set(value) != required:
        raise ImportValidationError(
            "Exactly projectShortName, stagingAreaIri, targetRootFolderIri, "
            "originalFileName, and compressedSizeBytes are required."
        )
    project = value["projectShortName"]
    if not isinstance(project, str) or PROJECT_SHORT_NAME_RE.fullmatch(project) is None:
        raise ImportValidationError("projectShortName is invalid.")
    staging_area = _validate_iri(value["stagingAreaIri"], "stagingAreaIri")
    target_folder = _validate_iri(value["targetRootFolderIri"], "targetRootFolderIri")
    original_name = value["originalFileName"]
    if not isinstance(original_name, str):
        raise ImportValidationError("originalFileName must be text.")
    original_name = unicodedata.normalize("NFC", original_name)
    if (
        not 1 <= len(original_name) <= 255
        or "\x00" in original_name
        or "\r" in original_name
        or "\n" in original_name
    ):
        raise ImportValidationError("originalFileName is invalid.")
    size = value["compressedSizeBytes"]
    if isinstance(size, bool) or not isinstance(size, int):
        raise ImportValidationError("compressedSizeBytes must be an integer.")
    if not 1 <= size <= MAX_COMPRESSED_BYTES:
        raise ImportPayloadTooLargeError(
            f"compressedSizeBytes must be between 1 and {MAX_COMPRESSED_BYTES}."
        )
    return {
        "projectShortName": project,
        "stagingAreaIri": staging_area,
        "targetRootFolderIri": target_folder,
        "originalFileName": original_name,
        "compressedSizeBytes": size,
    }


def _validate_iri(value: Any, field: str) -> str:
    """Validate one public staging-resource IRI without accepting unsafe schemes.

    OLDAP instance creation normally assigns canonical ``urn:uuid`` identifiers,
    while imported or externally managed resources may use HTTP(S) identifiers.
    Keeping this allowlist narrow prevents URI-shaped local-file or executable
    schemes from crossing the public import boundary.

    Args:
        value: Candidate JSON field value.
        field: Public field name used in validation errors.

    Returns:
        The unchanged, validated IRI.

    Raises:
        ImportValidationError: If the value is not an allowed absolute IRI.
    """
    if not isinstance(value, str) or not 1 <= len(value) <= 2048:
        raise ImportValidationError(f"{field} must be an absolute IRI.")
    if any(character in value for character in '<>"{}|\\^`\x00\r\n'):
        raise ImportValidationError(f"{field} contains unsafe characters.")

    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value

    urn_uuid_prefix = "urn:uuid:"
    if value.startswith(urn_uuid_prefix):
        identifier = value[len(urn_uuid_prefix) :]
        try:
            parsed_uuid = UUID(identifier)
        except (AttributeError, ValueError):
            pass
        else:
            if identifier == str(parsed_uuid):
                return value

    raise ImportValidationError(
        f"{field} must be an absolute HTTP(S) IRI or canonical UUID URN."
    )


def _validate_uuid(value: str) -> None:
    try:
        UUID(value)
    except (TypeError, ValueError) as error:
        raise ImportNotFoundError("Import job not found.") from error


def _validate_sip_stored_event(value: Any) -> SipStoredEvent:
    required = {"eventId", "storedAt", "sizeBytes", "sha256", "uploadRequestId"}
    if not isinstance(value, dict) or set(value) != required:
        raise ImportValidationError(
            "Exactly eventId, storedAt, sizeBytes, sha256, and uploadRequestId are required."
        )
    event_id = _canonical_uuid(value["eventId"], "eventId")
    upload_request_id = _canonical_uuid(value["uploadRequestId"], "uploadRequestId")
    size = value["sizeBytes"]
    if (
        isinstance(size, bool)
        or not isinstance(size, int)
        or not 1 <= size <= MAX_COMPRESSED_BYTES
    ):
        raise ImportValidationError("sizeBytes is outside the ZIP upload limit.")
    sha256 = value["sha256"]
    if not isinstance(sha256, str) or re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
        raise ImportValidationError("sha256 must be a lower-case SHA-256 digest.")
    try:
        stored_at = datetime.fromisoformat(
            str(value["storedAt"]).replace("Z", "+00:00")
        )
    except ValueError as error:
        raise ImportValidationError(
            "storedAt must be an ISO 8601 date-time."
        ) from error
    if stored_at.tzinfo is None:
        raise ImportValidationError("storedAt must include a timezone.")
    return SipStoredEvent(
        event_id=event_id,
        stored_at=stored_at.astimezone(UTC),
        size_bytes=size,
        sha256=sha256,
        upload_request_id=upload_request_id,
    )


def _canonical_uuid(value: Any, field: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError) as error:
        raise ImportValidationError(f"{field} must be a UUID.") from error


def _sip_receipt_matches(job: ImportJob, event: SipStoredEvent) -> bool:
    return (
        job.sip_stored_event_id == event.event_id
        and job.sip_sha256 == event.sha256
        and job.sip_upload_request_id == event.upload_request_id
        and job.actual_compressed_size_bytes == event.size_bytes
        and job.uploaded_at == event.stored_at
    )


def _validate_claim_request(
    value: Any,
) -> tuple[str, tuple[ImportTask, ...], int]:
    required = {"workerId", "supportedTasks"}
    if not isinstance(value, dict) or not required <= set(value) <= required | {
        "requestedLeaseSeconds"
    }:
        raise ImportValidationError(
            "workerId and supportedTasks are required; requestedLeaseSeconds is optional."
        )
    worker_id = value["workerId"]
    if (
        not isinstance(worker_id, str)
        or re.fullmatch(r"[A-Za-z0-9._-]{1,128}", worker_id) is None
    ):
        raise ImportValidationError("workerId is invalid.")
    raw_tasks = value["supportedTasks"]
    if (
        not isinstance(raw_tasks, list)
        or not raw_tasks
        or any(not isinstance(task, str) for task in raw_tasks)
        or len(set(raw_tasks)) != len(raw_tasks)
    ):
        raise ImportValidationError("supportedTasks must be a non-empty unique array.")
    try:
        tasks = tuple(ImportTask(task) for task in raw_tasks)
    except (TypeError, ValueError) as error:
        raise ImportValidationError(
            "supportedTasks contains an unknown task."
        ) from error
    lease_seconds = value.get("requestedLeaseSeconds", 300)
    if (
        isinstance(lease_seconds, bool)
        or not isinstance(lease_seconds, int)
        or not 60 <= lease_seconds <= 900
    ):
        raise ImportValidationError("requestedLeaseSeconds must be between 60 and 900.")
    return worker_id, tasks, lease_seconds


def _validate_heartbeat(value: Any) -> tuple[str, int]:
    if not isinstance(value, dict) or set(value) != {
        "workerId",
        "expectedStateVersion",
    }:
        raise ImportValidationError(
            "Exactly workerId and expectedStateVersion are required."
        )
    worker_id = value["workerId"]
    version = value["expectedStateVersion"]
    if (
        not isinstance(worker_id, str)
        or re.fullmatch(r"[A-Za-z0-9._-]{1,128}", worker_id) is None
    ):
        raise ImportValidationError("workerId is invalid.")
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise ImportValidationError("expectedStateVersion must be non-negative.")
    return worker_id, version


def _validate_target_preflight(
    value: Any,
) -> tuple[str, int, tuple[dict[str, Any], ...]]:
    """Validate the closed, bounded ZIP-root collision request."""

    required = {"workerId", "expectedStateVersion", "topLevelEntries"}
    if not isinstance(value, dict) or set(value) != required:
        raise ImportValidationError(
            "Exactly workerId, expectedStateVersion, and topLevelEntries are required."
        )
    worker_id = value["workerId"]
    version = value["expectedStateVersion"]
    entries = value["topLevelEntries"]
    if (
        not isinstance(worker_id, str)
        or re.fullmatch(r"[A-Za-z0-9._-]{1,128}", worker_id) is None
    ):
        raise ImportValidationError("workerId is invalid.")
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise ImportValidationError("expectedStateVersion must be non-negative.")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 10_000:
        raise ImportValidationError(
            "topLevelEntries must contain between 1 and 10000 entries."
        )
    normalized: list[dict[str, Any]] = []
    indexes: set[int] = set()
    keys: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "entryIndex",
            "name",
            "entryType",
        }:
            raise ImportValidationError("A top-level entry is invalid.")
        index = entry["entryIndex"]
        name = entry["name"]
        entry_type = entry["entryType"]
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or not 0 <= index <= 9_999
            or index in indexes
        ):
            raise ImportValidationError("top-level entryIndex is invalid or repeated.")
        if (
            not isinstance(name, str)
            or not name
            or len(name.encode("utf-8")) > 255
            or name != unicodedata.normalize("NFC", name)
            or any(character in name for character in ("/", "\\", "\x00"))
            or any(ord(character) < 32 or ord(character) == 127 for character in name)
            or name.endswith((" ", "."))
        ):
            raise ImportValidationError("top-level name is invalid.")
        key = _portable_name_key(name)
        if key in keys or entry_type not in {"file", "directory"}:
            raise ImportValidationError("top-level entry is ambiguous.")
        indexes.add(index)
        keys.add(key)
        normalized.append({"entryIndex": index, "name": name, "entryType": entry_type})
    return worker_id, version, tuple(normalized)


def _portable_name_key(value: str) -> str:
    """Match the ZIP validator's NFC and portable case-collision semantics."""

    return unicodedata.normalize("NFC", value).rstrip(" .").casefold()


def _bounded_utf8(value: str, max_bytes: int) -> str:
    """Truncate display evidence without splitting a UTF-8 code point."""

    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    shortened = encoded[:max_bytes]
    while shortened:
        try:
            return shortened.decode("utf-8")
        except UnicodeDecodeError:
            shortened = shortened[:-1]
    return "?"


def _claim_from_job(job: ImportJob) -> ImportClaim:
    if (
        not job.active_claim_id
        or not job.active_claim_task
        or not job.active_claimed_at
        or not job.active_claim_lease_expires_at
    ):
        raise RuntimeError("Persisted claim is incomplete.")
    cleanup_reason = (
        _cleanup_reason(job) if job.active_claim_task == "CLEANUP" else None
    )
    return ImportClaim(
        claim_id=job.active_claim_id,
        import_id=job.import_id,
        task=ImportTask(job.active_claim_task),
        state_version=job.state_version,
        claimed_at=job.active_claimed_at,
        lease_expires_at=job.active_claim_lease_expires_at,
        target=job.target,
        job_created_at=job.created_at,
        requested_by_iri=job.requested_by_iri,
        original_file_name=job.original_file_name,
        compressed_size_bytes=(
            job.actual_compressed_size_bytes or job.declared_compressed_size_bytes
        ),
        sip_sha256=job.sip_sha256,
        manifest_sha256=job.manifest_sha256,
        cleanup_reason=cleanup_reason,
    )


def _cleanup_reason(job: ImportJob) -> str:
    """Return the closed cleanup outcome selected by authoritative job state."""

    if job.state in {ImportState.UPLOADING, ImportState.READY}:
        return ImportState.EXPIRED.value
    if job.state in {
        ImportState.CANCELLED,
        ImportState.IMPORTED,
        ImportState.FAILED,
        ImportState.EXPIRED,
    }:
        return job.state.value
    raise ImportStateConflict("The current state has no cleanup reason.")


def _validate_validation_result(value: Any) -> tuple[dict[str, Any], str]:
    required = {
        "eventId",
        "claimId",
        "expectedStateVersion",
        "outcome",
        "completedAt",
        "temporaryPayloadDeleted",
        "reportSha256",
        "summary",
    }
    optional = {"manifestSha256", "failureCode"}
    if not isinstance(value, dict) or not required <= set(value) <= required | optional:
        raise ImportValidationError("The validation-result fields are invalid.")
    normalized = dict(value)
    normalized["eventId"] = _canonical_uuid(value["eventId"], "eventId")
    normalized["claimId"] = _canonical_uuid(value["claimId"], "claimId")
    version = value["expectedStateVersion"]
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise ImportValidationError("expectedStateVersion must be non-negative.")
    try:
        outcome = ImportState(value["outcome"])
    except (TypeError, ValueError) as error:
        raise ImportValidationError(
            "outcome must be READY, INVALID, or FAILED."
        ) from error
    if outcome not in {ImportState.READY, ImportState.INVALID, ImportState.FAILED}:
        raise ImportValidationError("outcome must be READY, INVALID, or FAILED.")
    normalized["outcome"] = outcome.value
    try:
        completed_at = datetime.fromisoformat(
            str(value["completedAt"]).replace("Z", "+00:00")
        )
    except ValueError as error:
        raise ImportValidationError(
            "completedAt must be an ISO 8601 date-time."
        ) from error
    if completed_at.tzinfo is None:
        raise ImportValidationError("completedAt must include a timezone.")
    normalized["completedAt"] = completed_at.astimezone(UTC)
    for field in ("reportSha256", "manifestSha256"):
        if field in value and (
            not isinstance(value[field], str)
            or re.fullmatch(r"[0-9a-f]{64}", value[field]) is None
        ):
            raise ImportValidationError(f"{field} must be a lower-case SHA-256 digest.")
    if outcome is ImportState.READY:
        if (
            value.get("temporaryPayloadDeleted") is not False
            or "manifestSha256" not in value
        ):
            raise ImportValidationError(
                "READY requires retained payload and manifestSha256."
            )
    elif value.get("temporaryPayloadDeleted") is not True:
        raise ImportValidationError("INVALID/FAILED require deleted temporary payload.")
    if outcome is ImportState.FAILED:
        if "manifestSha256" in value or not _valid_failure_code(
            value.get("failureCode")
        ):
            raise ImportValidationError(
                "FAILED requires failureCode and no manifestSha256."
            )
    elif "manifestSha256" not in value:
        raise ImportValidationError("READY/INVALID require manifestSha256.")
    normalized["summary"] = _validate_summary(value["summary"])
    canonical = dict(normalized)
    canonical["completedAt"] = normalized["completedAt"].isoformat()
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return normalized, digest


def _validate_summary(value: Any) -> dict[str, Any]:
    required = {
        "entriesObserved",
        "inventoryComplete",
        "files",
        "directories",
        "importableFiles",
        "importableDirectories",
        "ignoredEntries",
        "rejectedEntries",
        "warningCount",
        "errorCount",
        "compressedBytes",
        "extractedBytes",
        "maxDepth",
    }
    allowed = required | {"entriesDeclared"}
    if not isinstance(value, dict) or not required <= set(value) <= allowed:
        raise ImportValidationError("summary does not match ValidationSummary.")
    if not isinstance(value["inventoryComplete"], bool):
        raise ImportValidationError("summary.inventoryComplete must be boolean.")
    for key, item in value.items():
        if key == "inventoryComplete":
            continue
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise ImportValidationError(f"summary.{key} must be non-negative.")
    if value["extractedBytes"] > 3_000_000_000:
        raise ImportValidationError("summary.extractedBytes exceeds the MVP limit.")
    return dict(value)


def _valid_failure_code(value: Any) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", value) is not None
    )


def _bounded_error(value: str | None) -> str:
    normalized = " ".join(str(value or "Mail submission failed.").split())
    return normalized[:300]


def _encode_cursor(job: ImportJob) -> str:
    """Encode the last visible sort key without exposing persistence details."""
    payload = json.dumps(
        {
            "createdAt": job.created_at.astimezone(UTC).isoformat(),
            "importId": job.import_id,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    """Validate and decode an opaque list cursor into its stable sort key."""
    if not cursor or len(cursor) > MAX_CURSOR_LENGTH or not cursor.isascii():
        raise ImportValidationError("cursor is invalid.")
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict) or set(value) != {"createdAt", "importId"}:
            raise ValueError
        created_at = datetime.fromisoformat(str(value["createdAt"]))
        if created_at.tzinfo is None:
            raise ValueError
        import_id = str(value["importId"])
        _validate_uuid(import_id)
    except (
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        raise ImportValidationError("cursor is invalid.") from error
    return created_at.astimezone(UTC), import_id
