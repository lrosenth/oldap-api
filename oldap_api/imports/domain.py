"""Immutable value objects and lifecycle rules for ZIP import jobs."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping

MAX_COMPRESSED_BYTES = 500_000_000
MAX_EXTRACTED_BYTES = 3_000_000_000
MAX_AGGREGATE_COMPRESSION_RATIO = 50


class ImportState(StrEnum):
    """Authoritative lifecycle states of one immutable ZIP import."""

    UPLOADING = "UPLOADING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    IMPORTING = "IMPORTING"
    IMPORTED = "IMPORTED"
    INVALID = "INVALID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ImportTask(StrEnum):
    """Sequential worker tasks selected by the API queue."""

    VALIDATE = "VALIDATE"
    IMPORT = "IMPORT"
    CLEANUP = "CLEANUP"


class NotificationStatus(StrEnum):
    """Submission state independent from the import lifecycle."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


TERMINAL_STATES = frozenset(
    {
        ImportState.IMPORTED,
        ImportState.INVALID,
        ImportState.FAILED,
        ImportState.CANCELLED,
        ImportState.EXPIRED,
    }
)

ALLOWED_TRANSITIONS: Mapping[ImportState, frozenset[ImportState]] = {
    ImportState.UPLOADING: frozenset(
        {ImportState.VALIDATING, ImportState.CANCELLED, ImportState.EXPIRED}
    ),
    ImportState.VALIDATING: frozenset(
        {ImportState.READY, ImportState.INVALID, ImportState.FAILED}
    ),
    ImportState.READY: frozenset(
        {ImportState.IMPORTING, ImportState.CANCELLED, ImportState.EXPIRED}
    ),
    ImportState.IMPORTING: frozenset({ImportState.IMPORTED, ImportState.FAILED}),
}


class ImportDomainError(ValueError):
    """Base class for stable import-domain conflicts."""

    code = "IMPORT_CONFLICT"


class ImportStateConflict(ImportDomainError):
    """Raised when an action is invalid in the current lifecycle state."""

    code = "IMPORT_STATE_CONFLICT"


class ImportVersionConflict(ImportDomainError):
    """Raised when optimistic state versions do not match."""

    code = "IMPORT_VERSION_CONFLICT"


class ImportEventConflict(ImportDomainError):
    """Raised when an internal event conflicts with the accepted receipt."""

    code = "IMPORT_EVENT_CONFLICT"


class ImportClaimConflict(ImportDomainError):
    """Raised when a worker lease is missing, stale, or owned elsewhere."""

    code = "IMPORT_CLAIM_CONFLICT"


@dataclass(frozen=True, slots=True)
class TargetSnapshot:
    """Immutable identity and display snapshot of the selected staging target."""

    project_short_name: str
    staging_area_iri: str
    staging_area_name: str
    target_root_folder_iri: str
    target_root_folder_name: str

    def to_dict(self) -> dict[str, str]:
        """Return the public camel-case API representation."""
        return {
            "projectShortName": self.project_short_name,
            "stagingAreaIri": self.staging_area_iri,
            "stagingAreaName": self.staging_area_name,
            "targetRootFolderIri": self.target_root_folder_iri,
            "targetRootFolderName": self.target_root_folder_name,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TargetSnapshot:
        """Restore a snapshot from its persisted/API representation."""
        return cls(
            project_short_name=str(value["projectShortName"]),
            staging_area_iri=str(value["stagingAreaIri"]),
            staging_area_name=str(value["stagingAreaName"]),
            target_root_folder_iri=str(value["targetRootFolderIri"]),
            target_root_folder_name=str(value["targetRootFolderName"]),
        )


@dataclass(frozen=True, slots=True)
class ImportClaim:
    """One renewable lease over a single import task."""

    claim_id: str
    import_id: str
    task: ImportTask
    state_version: int
    claimed_at: datetime
    lease_expires_at: datetime
    target: TargetSnapshot
    job_created_at: datetime
    requested_by_iri: str
    original_file_name: str
    compressed_size_bytes: int
    sip_sha256: str | None = None
    manifest_sha256: str | None = None
    cleanup_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "claimId": self.claim_id,
            "importId": self.import_id,
            "task": self.task.value,
            "stateVersion": self.state_version,
            "claimedAt": _format_datetime(self.claimed_at),
            "leaseExpiresAt": _format_datetime(self.lease_expires_at),
            "target": self.target.to_dict(),
            "jobCreatedAt": _format_datetime(self.job_created_at),
            "requestedByIri": self.requested_by_iri,
            "originalFileName": self.original_file_name,
            "compressedSizeBytes": self.compressed_size_bytes,
        }
        if self.sip_sha256:
            result["sipSha256"] = self.sip_sha256
        if self.manifest_sha256:
            result["manifestSha256"] = self.manifest_sha256
        if self.cleanup_reason:
            result["cleanupReason"] = self.cleanup_reason
        return result


@dataclass(frozen=True, slots=True)
class ImportJob:
    """Complete durable state of one ZIP import request.

    ``state_version`` changes with every accepted lifecycle mutation. Timestamps
    and optional results are kept on the job so clients never need filesystem
    state to interpret the workflow.
    """

    import_id: str
    state: ImportState
    state_version: int
    created_at: datetime
    updated_at: datetime
    requested_by_iri: str
    requested_by_user_id: str
    target: TargetSnapshot
    original_file_name: str
    declared_compressed_size_bytes: int
    quota_reserved_bytes: int
    uploaded_at: datetime | None = None
    validation_completed_at: datetime | None = None
    imported_at: datetime | None = None
    expires_at: datetime | None = None
    actual_compressed_size_bytes: int | None = None
    extracted_size_bytes: int | None = None
    report_available: bool = False
    cleanup_pending: bool = False
    summary: Mapping[str, Any] | None = None
    failure_code: str | None = None
    sip_sha256: str | None = None
    sip_upload_request_id: str | None = None
    sip_stored_event_id: str | None = None
    active_claim_id: str | None = None
    active_claim_task: str | None = None
    active_claim_worker_id: str | None = None
    active_claimed_at: datetime | None = None
    active_claim_lease_expires_at: datetime | None = None
    validation_event_id: str | None = None
    validation_result_digest: str | None = None
    validation_outcome: ImportState | None = None
    manifest_sha256: str | None = None
    report_sha256: str | None = None
    import_event_id: str | None = None
    import_result_digest: str | None = None
    imported_resources: tuple[Mapping[str, Any], ...] = ()
    task_failure_event_id: str | None = None
    task_failure_digest: str | None = None
    cleanup_event_id: str | None = None
    cleanup_result_digest: str | None = None
    notification_status: NotificationStatus | None = None
    notification_for_state: ImportState | None = None
    notification_attempts: int = 0
    notification_sent_at: datetime | None = None
    notification_last_attempt_at: datetime | None = None
    notification_last_error: str | None = None

    @property
    def can_confirm(self) -> bool:
        """Return whether the job is READY and has not expired."""
        return (
            self.state is ImportState.READY
            and self.expires_at is not None
            and self.expires_at > datetime.now(UTC)
        )

    def transition(
        self,
        target_state: ImportState,
        *,
        expected_state_version: int,
        now: datetime | None = None,
        **changes: Any,
    ) -> ImportJob:
        """Return a new job after validating an optimistic state transition.

        Args:
            target_state: Required next lifecycle state.
            expected_state_version: Version observed by the caller.
            now: Mutation time, injectable for deterministic tests.
            **changes: State-specific persisted field updates.

        Raises:
            ImportVersionConflict: If the caller observed a stale version.
            ImportStateConflict: If the transition is not allowed.
        """
        if expected_state_version != self.state_version:
            raise ImportVersionConflict(
                f"Expected state version {expected_state_version}, current version is "
                f"{self.state_version}."
            )
        if target_state not in ALLOWED_TRANSITIONS.get(self.state, frozenset()):
            raise ImportStateConflict(
                f"Cannot transition import from {self.state} to {target_state}."
            )
        return replace(
            self,
            state=target_state,
            state_version=self.state_version + 1,
            updated_at=now or datetime.now(UTC),
            **changes,
        )

    def to_dict(self, *, internal: bool = False) -> dict[str, Any]:
        """Return the public contract, optionally including internal ownership."""
        result: dict[str, Any] = {
            "importId": self.import_id,
            "state": self.state.value,
            "stateVersion": self.state_version,
            "createdAt": _format_datetime(self.created_at),
            "updatedAt": _format_datetime(self.updated_at),
            "requestedByIri": self.requested_by_iri,
            "target": self.target.to_dict(),
            "originalFileName": self.original_file_name,
            "declaredCompressedSizeBytes": self.declared_compressed_size_bytes,
            "quotaReservedBytes": self.quota_reserved_bytes,
            "reportAvailable": self.report_available,
            "canConfirm": self.can_confirm,
            "cleanupPending": self.cleanup_pending,
        }
        optional = {
            "uploadedAt": self.uploaded_at,
            "validationCompletedAt": self.validation_completed_at,
            "importedAt": self.imported_at,
            "expiresAt": self.expires_at,
        }
        result.update(
            {key: _format_datetime(value) for key, value in optional.items() if value}
        )
        scalar_optional = {
            "actualCompressedSizeBytes": self.actual_compressed_size_bytes,
            "extractedSizeBytes": self.extracted_size_bytes,
            "summary": self.summary,
            "failureCode": self.failure_code,
        }
        result.update(
            {key: value for key, value in scalar_optional.items() if value is not None}
        )
        if internal:
            result["requestedByUserId"] = self.requested_by_user_id
            internal_optional = {
                "sipSha256": self.sip_sha256,
                "sipUploadRequestId": self.sip_upload_request_id,
                "sipStoredEventId": self.sip_stored_event_id,
                "activeClaimId": self.active_claim_id,
                "activeClaimTask": self.active_claim_task,
                "activeClaimWorkerId": self.active_claim_worker_id,
                "activeClaimedAt": (
                    _format_datetime(self.active_claimed_at)
                    if self.active_claimed_at
                    else None
                ),
                "activeClaimLeaseExpiresAt": (
                    _format_datetime(self.active_claim_lease_expires_at)
                    if self.active_claim_lease_expires_at
                    else None
                ),
                "validationEventId": self.validation_event_id,
                "validationResultDigest": self.validation_result_digest,
                "validationOutcome": (
                    self.validation_outcome.value if self.validation_outcome else None
                ),
                "manifestSha256": self.manifest_sha256,
                "reportSha256": self.report_sha256,
                "importEventId": self.import_event_id,
                "importResultDigest": self.import_result_digest,
                "importedResources": (
                    [dict(resource) for resource in self.imported_resources]
                    if self.imported_resources
                    else None
                ),
                "taskFailureEventId": self.task_failure_event_id,
                "taskFailureDigest": self.task_failure_digest,
                "cleanupEventId": self.cleanup_event_id,
                "cleanupResultDigest": self.cleanup_result_digest,
                "notificationLastError": self.notification_last_error,
                "notificationLastAttemptAt": (
                    _format_datetime(self.notification_last_attempt_at)
                    if self.notification_last_attempt_at
                    else None
                ),
            }
            result.update(
                {
                    key: value
                    for key, value in internal_optional.items()
                    if value is not None
                }
            )
        if self.notification_status is not None:
            result["notification"] = {
                "status": self.notification_status.value,
                "forState": (
                    self.notification_for_state.value
                    if self.notification_for_state
                    else self.state.value
                ),
                "attempts": self.notification_attempts,
                **(
                    {"sentAt": _format_datetime(self.notification_sent_at)}
                    if self.notification_sent_at
                    else {}
                ),
            }
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ImportJob:
        """Restore a job from its canonical persisted representation."""
        return cls(
            import_id=str(value["importId"]),
            state=ImportState(value["state"]),
            state_version=int(value["stateVersion"]),
            created_at=_parse_datetime(value["createdAt"]),
            updated_at=_parse_datetime(value["updatedAt"]),
            requested_by_iri=str(value["requestedByIri"]),
            requested_by_user_id=str(value["requestedByUserId"]),
            target=TargetSnapshot.from_dict(value["target"]),
            original_file_name=str(value["originalFileName"]),
            declared_compressed_size_bytes=int(value["declaredCompressedSizeBytes"]),
            quota_reserved_bytes=int(value["quotaReservedBytes"]),
            uploaded_at=_parse_optional_datetime(value.get("uploadedAt")),
            validation_completed_at=_parse_optional_datetime(
                value.get("validationCompletedAt")
            ),
            imported_at=_parse_optional_datetime(value.get("importedAt")),
            expires_at=_parse_optional_datetime(value.get("expiresAt")),
            actual_compressed_size_bytes=value.get("actualCompressedSizeBytes"),
            extracted_size_bytes=value.get("extractedSizeBytes"),
            report_available=bool(value.get("reportAvailable", False)),
            cleanup_pending=bool(value.get("cleanupPending", False)),
            summary=value.get("summary"),
            failure_code=value.get("failureCode"),
            sip_sha256=value.get("sipSha256"),
            sip_upload_request_id=value.get("sipUploadRequestId"),
            sip_stored_event_id=value.get("sipStoredEventId"),
            active_claim_id=value.get("activeClaimId"),
            active_claim_task=value.get("activeClaimTask"),
            active_claim_worker_id=value.get("activeClaimWorkerId"),
            active_claimed_at=_parse_optional_datetime(value.get("activeClaimedAt")),
            active_claim_lease_expires_at=_parse_optional_datetime(
                value.get("activeClaimLeaseExpiresAt")
            ),
            validation_event_id=value.get("validationEventId"),
            validation_result_digest=value.get("validationResultDigest"),
            validation_outcome=(
                ImportState(value["validationOutcome"])
                if value.get("validationOutcome")
                else None
            ),
            manifest_sha256=value.get("manifestSha256"),
            report_sha256=value.get("reportSha256"),
            import_event_id=value.get("importEventId"),
            import_result_digest=value.get("importResultDigest"),
            imported_resources=tuple(value.get("importedResources", ())),
            task_failure_event_id=value.get("taskFailureEventId"),
            task_failure_digest=value.get("taskFailureDigest"),
            cleanup_event_id=value.get("cleanupEventId"),
            cleanup_result_digest=value.get("cleanupResultDigest"),
            notification_status=(
                NotificationStatus(value["notification"]["status"])
                if value.get("notification")
                else None
            ),
            notification_for_state=(
                ImportState(value["notification"]["forState"])
                if value.get("notification")
                else None
            ),
            notification_attempts=(
                int(value["notification"].get("attempts", 0))
                if value.get("notification")
                else 0
            ),
            notification_sent_at=(
                _parse_optional_datetime(value["notification"].get("sentAt"))
                if value.get("notification")
                else None
            ),
            notification_last_attempt_at=_parse_optional_datetime(
                value.get("notificationLastAttemptAt")
            ),
            notification_last_error=value.get("notificationLastError"),
        )


def conservative_quota_reservation(compressed_size_bytes: int) -> int:
    """Calculate the agreed pre-validation extracted-byte reservation."""
    if not 1 <= compressed_size_bytes <= MAX_COMPRESSED_BYTES:
        raise ValueError(
            f"compressedSizeBytes must be between 1 and {MAX_COMPRESSED_BYTES}."
        )
    return min(
        MAX_EXTRACTED_BYTES,
        compressed_size_bytes * MAX_AGGREGATE_COMPRESSION_RATIO,
    )


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Persisted import timestamps must include a timezone.")
    return parsed.astimezone(UTC)


def _parse_optional_datetime(value: Any) -> datetime | None:
    return _parse_datetime(value) if value is not None else None
