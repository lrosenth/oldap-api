"""Immutable project-neutral lifecycle vocabulary for ZIP exports.

Phase 0 deliberately defines no persistence or HTTP behavior. These values are
the shared language for the later API repository, media-local worker, OpenAPI
contract, and project frontends.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping

MAX_EXPORT_BYTES = 50_000_000_000
READY_RETENTION_HOURS = 24
AUDIT_RETENTION_DAYS = 60


class ExportKind(StrEnum):
    """Closed project-neutral selection scopes supported by export v1."""

    STAGING_FOLDER = "STAGING_FOLDER"
    STAGING_ALL = "STAGING_ALL"
    ARCHIVE_UNIT = "ARCHIVE_UNIT"
    ARCHIVE_ALL = "ARCHIVE_ALL"


class ExportState(StrEnum):
    """Authoritative lifecycle states for one asynchronous export job."""

    QUEUED = "QUEUED"
    BUILDING = "BUILDING"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    DELETING = "DELETING"
    DELETED = "DELETED"


class ExportTask(StrEnum):
    """Tasks claimable by the media-local export worker."""

    BUILD = "BUILD"
    CLEANUP = "CLEANUP"


class ExportNotificationStatus(StrEnum):
    """Submission state independent from the export lifecycle."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


ALLOWED_EXPORT_TRANSITIONS: Mapping[ExportState, frozenset[ExportState]] = {
    ExportState.QUEUED: frozenset(
        {ExportState.BUILDING, ExportState.CANCELLED, ExportState.FAILED}
    ),
    ExportState.BUILDING: frozenset(
        {ExportState.READY, ExportState.CANCELLED, ExportState.FAILED}
    ),
    ExportState.READY: frozenset({ExportState.EXPIRED, ExportState.DELETING}),
    ExportState.FAILED: frozenset({ExportState.DELETING}),
    ExportState.CANCELLED: frozenset({ExportState.DELETING}),
    ExportState.EXPIRED: frozenset({ExportState.DELETING}),
    ExportState.DELETING: frozenset({ExportState.DELETED}),
}


class ExportStateConflict(ValueError):
    """Raised when a lifecycle transition is not part of export v1."""


class ExportVersionConflict(ValueError):
    """Raised when an action uses a stale optimistic state version."""


@dataclass(frozen=True, slots=True)
class ExportSelectionSnapshot:
    """Immutable authorized selection and profile identity."""

    project_short_name: str
    kind: ExportKind
    display_name: str
    display_path: str
    profile_id: str
    profile_version: str
    profile_sha256: str
    metadata_schema_version: str = "1.0.0"
    selection_iri: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Return the public API representation."""

        result = {
            "projectShortName": self.project_short_name,
            "kind": self.kind.value,
            "displayName": self.display_name,
            "displayPath": self.display_path,
            "profileId": self.profile_id,
            "profileVersion": self.profile_version,
            "profileSha256": self.profile_sha256,
            "metadataSchemaVersion": self.metadata_schema_version,
        }
        if self.selection_iri:
            result["selectionIri"] = self.selection_iri
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExportSelectionSnapshot":
        """Restore a selection snapshot from durable canonical JSON."""

        return cls(
            project_short_name=str(value["projectShortName"]),
            kind=ExportKind(value["kind"]),
            display_name=str(value["displayName"]),
            display_path=str(value["displayPath"]),
            profile_id=str(value["profileId"]),
            profile_version=str(value["profileVersion"]),
            profile_sha256=str(value["profileSha256"]),
            metadata_schema_version=str(value["metadataSchemaVersion"]),
            selection_iri=(
                str(value["selectionIri"])
                if value.get("selectionIri") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class ExportProgress:
    """Bounded worker progress facts safe for public polling."""

    files_done: int = 0
    files_total: int = 0
    bytes_done: int = 0
    bytes_total: int = 0

    def __post_init__(self) -> None:
        values = (self.files_done, self.files_total, self.bytes_done, self.bytes_total)
        if any(value < 0 for value in values):
            raise ValueError("Export progress values must not be negative.")
        if self.files_done > self.files_total or self.bytes_done > self.bytes_total:
            raise ValueError("Export progress must not exceed its totals.")

    def to_dict(self) -> dict[str, int]:
        """Return the public API representation."""

        return {
            "filesDone": self.files_done,
            "filesTotal": self.files_total,
            "bytesDone": self.bytes_done,
            "bytesTotal": self.bytes_total,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExportProgress":
        """Restore bounded progress facts from durable canonical JSON."""

        return cls(
            files_done=int(value["filesDone"]),
            files_total=int(value["filesTotal"]),
            bytes_done=int(value["bytesDone"]),
            bytes_total=int(value["bytesTotal"]),
        )


@dataclass(frozen=True, slots=True)
class ExportJob:
    """Durable state of one project-neutral ZIP export request."""

    export_id: str
    state: ExportState
    state_version: int
    created_at: datetime
    updated_at: datetime
    requested_by_iri: str
    requested_by_user_id: str
    selection: ExportSelectionSnapshot
    estimated_source_bytes: int
    warning_count: int = 0
    progress: ExportProgress = ExportProgress()
    snapshot_at: datetime | None = None
    manifest_sha256: str | None = None
    ready_at: datetime | None = None
    expires_at: datetime | None = None
    archive_size_bytes: int | None = None
    archive_sha256: str | None = None
    failure_code: str | None = None
    deleted_at: datetime | None = None
    audit_delete_at: datetime | None = None
    active_claim_id: str | None = None
    active_claim_task: ExportTask | None = None
    active_claim_worker_id: str | None = None
    active_claimed_at: datetime | None = None
    active_claim_lease_expires_at: datetime | None = None
    active_claim_lease_seconds: int | None = None
    cleanup_reason: str | None = None
    build_event_id: str | None = None
    build_result_digest: str | None = None
    cleanup_event_id: str | None = None
    cleanup_result_digest: str | None = None
    notification_status: ExportNotificationStatus | None = None
    notification_for_state: ExportState | None = None
    notification_attempts: int = 0
    notification_sent_at: datetime | None = None
    notification_last_attempt_at: datetime | None = None
    notification_last_error: str | None = None

    def __post_init__(self) -> None:
        if self.state_version < 0:
            raise ValueError("stateVersion must not be negative.")
        if not 0 <= self.estimated_source_bytes <= MAX_EXPORT_BYTES:
            raise ValueError("Estimated export bytes exceed the v1 limit.")
        if self.warning_count < 0:
            raise ValueError("warningCount must not be negative.")
        if self.archive_size_bytes is not None and not (
            1 <= self.archive_size_bytes <= MAX_EXPORT_BYTES
        ):
            raise ValueError("Archive size exceeds the v1 limit.")
        if self.state is ExportState.READY and not all(
            (
                self.ready_at,
                self.expires_at,
                self.archive_size_bytes,
                self.archive_sha256,
                self.manifest_sha256,
            )
        ):
            raise ValueError("READY exports require complete artifact evidence.")
        if self.state is ExportState.DELETED and not self.deleted_at:
            raise ValueError("DELETED exports require deletedAt proof.")
        claim_values = (
            self.active_claim_id,
            self.active_claim_task,
            self.active_claim_worker_id,
            self.active_claimed_at,
            self.active_claim_lease_expires_at,
            self.active_claim_lease_seconds,
        )
        if any(value is not None for value in claim_values) and not all(
            value is not None for value in claim_values
        ):
            raise ValueError("Active export claim fields must be complete.")
        if self.active_claim_task is ExportTask.CLEANUP:
            if not self.cleanup_reason:
                raise ValueError("CLEANUP claims require a cleanup reason.")
        if (
            self.active_claimed_at is not None
            and self.active_claim_lease_expires_at is not None
            and self.active_claim_lease_expires_at <= self.active_claimed_at
        ):
            raise ValueError("Active export lease must expire after claim time.")
        if self.active_claim_lease_seconds is not None and not (
            60 <= self.active_claim_lease_seconds <= 900
        ):
            raise ValueError("Active export lease seconds must be between 60 and 900.")
        if not 0 <= self.notification_attempts <= 3:
            raise ValueError("Export notification attempts must be between 0 and 3.")
        if self.notification_status is None:
            if (
                any(
                    value is not None
                    for value in (
                        self.notification_for_state,
                        self.notification_sent_at,
                        self.notification_last_attempt_at,
                        self.notification_last_error,
                    )
                )
                or self.notification_attempts
            ):
                raise ValueError("Export notification fields must be absent together.")
        elif self.notification_for_state not in {
            ExportState.READY,
            ExportState.FAILED,
        }:
            raise ValueError("Export notifications support READY or FAILED only.")
        if (
            self.notification_status is ExportNotificationStatus.SENT
            and self.notification_sent_at is None
        ):
            raise ValueError("SENT export notifications require sentAt.")

    def can_download(self, *, now: datetime | None = None) -> bool:
        """Return whether a READY artifact is still inside its retention window."""

        current = now or datetime.now(UTC)
        return (
            self.state is ExportState.READY
            and self.expires_at is not None
            and self.expires_at > current
        )

    def transition(
        self,
        target: ExportState,
        *,
        expected_state_version: int,
        now: datetime | None = None,
        **changes: Any,
    ) -> "ExportJob":
        """Return a new immutable job after an optimistic state transition."""

        if expected_state_version != self.state_version:
            raise ExportVersionConflict(
                f"Expected state version {expected_state_version}, current version is "
                f"{self.state_version}."
            )
        allowed_export_transition(self.state, target)
        return replace(
            self,
            state=target,
            state_version=self.state_version + 1,
            updated_at=now or datetime.now(UTC),
            **changes,
        )

    def to_dict(
        self, *, internal: bool = False, now: datetime | None = None
    ) -> dict[str, Any]:
        """Return the public contract, optionally including worker-only facts."""

        result: dict[str, Any] = {
            "exportId": self.export_id,
            "state": self.state.value,
            "stateVersion": self.state_version,
            "createdAt": _format_datetime(self.created_at),
            "updatedAt": _format_datetime(self.updated_at),
            "requestedByIri": self.requested_by_iri,
            "selection": self.selection.to_dict(),
            "estimatedSourceBytes": self.estimated_source_bytes,
            "warningCount": self.warning_count,
            "progress": self.progress.to_dict(),
            "canDownload": self.can_download(now=now),
            "canDelete": self.state not in {ExportState.DELETING, ExportState.DELETED},
        }
        timestamps = {
            "snapshotAt": self.snapshot_at,
            "readyAt": self.ready_at,
            "expiresAt": self.expires_at,
            "deletedAt": self.deleted_at,
            "auditDeleteAt": self.audit_delete_at,
        }
        result.update(
            {key: _format_datetime(value) for key, value in timestamps.items() if value}
        )
        scalars = {
            "archiveSizeBytes": self.archive_size_bytes,
            "archiveSha256": self.archive_sha256,
            "failureCode": self.failure_code,
        }
        result.update(
            {key: value for key, value in scalars.items() if value is not None}
        )
        if internal:
            result["requestedByUserId"] = self.requested_by_user_id
            if self.manifest_sha256:
                result["manifestSha256"] = self.manifest_sha256
            internal_values = {
                "activeClaimId": self.active_claim_id,
                "activeClaimTask": (
                    self.active_claim_task.value if self.active_claim_task else None
                ),
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
                "activeClaimLeaseSeconds": self.active_claim_lease_seconds,
                "cleanupReason": self.cleanup_reason,
                "buildEventId": self.build_event_id,
                "buildResultDigest": self.build_result_digest,
                "cleanupEventId": self.cleanup_event_id,
                "cleanupResultDigest": self.cleanup_result_digest,
                "notificationLastAttemptAt": (
                    _format_datetime(self.notification_last_attempt_at)
                    if self.notification_last_attempt_at
                    else None
                ),
                "notificationLastError": self.notification_last_error,
            }
            result.update(
                {
                    key: value
                    for key, value in internal_values.items()
                    if value is not None
                }
            )
        if self.notification_status is not None:
            result["notification"] = {
                "status": self.notification_status.value,
                "forState": self.notification_for_state.value,
                "attempts": self.notification_attempts,
                **(
                    {"sentAt": _format_datetime(self.notification_sent_at)}
                    if self.notification_sent_at
                    else {}
                ),
            }
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExportJob":
        """Restore a job from its complete internal persisted representation."""

        return cls(
            export_id=str(value["exportId"]),
            state=ExportState(value["state"]),
            state_version=int(value["stateVersion"]),
            created_at=_parse_datetime(value["createdAt"]),
            updated_at=_parse_datetime(value["updatedAt"]),
            requested_by_iri=str(value["requestedByIri"]),
            requested_by_user_id=str(value["requestedByUserId"]),
            selection=ExportSelectionSnapshot.from_dict(value["selection"]),
            estimated_source_bytes=int(value["estimatedSourceBytes"]),
            warning_count=int(value.get("warningCount", 0)),
            progress=ExportProgress.from_dict(value["progress"]),
            snapshot_at=_parse_optional_datetime(value.get("snapshotAt")),
            manifest_sha256=value.get("manifestSha256"),
            ready_at=_parse_optional_datetime(value.get("readyAt")),
            expires_at=_parse_optional_datetime(value.get("expiresAt")),
            archive_size_bytes=value.get("archiveSizeBytes"),
            archive_sha256=value.get("archiveSha256"),
            failure_code=value.get("failureCode"),
            deleted_at=_parse_optional_datetime(value.get("deletedAt")),
            audit_delete_at=_parse_optional_datetime(value.get("auditDeleteAt")),
            active_claim_id=value.get("activeClaimId"),
            active_claim_task=(
                ExportTask(value["activeClaimTask"])
                if value.get("activeClaimTask") is not None
                else None
            ),
            active_claim_worker_id=value.get("activeClaimWorkerId"),
            active_claimed_at=_parse_optional_datetime(value.get("activeClaimedAt")),
            active_claim_lease_expires_at=_parse_optional_datetime(
                value.get("activeClaimLeaseExpiresAt")
            ),
            active_claim_lease_seconds=value.get("activeClaimLeaseSeconds"),
            cleanup_reason=value.get("cleanupReason"),
            build_event_id=value.get("buildEventId"),
            build_result_digest=value.get("buildResultDigest"),
            cleanup_event_id=value.get("cleanupEventId"),
            cleanup_result_digest=value.get("cleanupResultDigest"),
            notification_status=(
                ExportNotificationStatus(value["notification"]["status"])
                if value.get("notification")
                else None
            ),
            notification_for_state=(
                ExportState(value["notification"]["forState"])
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

    def to_persisted_dict(self) -> dict[str, Any]:
        """Return canonical durable state without time-dependent UI flags."""

        result = self.to_dict(internal=True)
        result.pop("canDownload")
        result.pop("canDelete")
        return result


@dataclass(frozen=True, slots=True)
class ExportClaim:
    """One renewable media-worker lease over BUILD or CLEANUP."""

    claim_id: str
    export_id: str
    task: ExportTask
    state_version: int
    claimed_at: datetime
    lease_expires_at: datetime
    manifest_sha256: str | None = None
    cleanup_reason: str | None = None

    def __post_init__(self) -> None:
        if self.lease_expires_at <= self.claimed_at:
            raise ValueError("Export claim lease must expire after it is claimed.")
        if self.task is ExportTask.BUILD:
            if not self.manifest_sha256 or self.cleanup_reason is not None:
                raise ValueError(
                    "BUILD claims require manifestSha256 and no cleanupReason."
                )
        elif not self.cleanup_reason or self.manifest_sha256 is not None:
            raise ValueError(
                "CLEANUP claims require cleanupReason and no manifestSha256."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return the internal API representation."""

        result: dict[str, Any] = {
            "claimId": self.claim_id,
            "exportId": self.export_id,
            "task": self.task.value,
            "stateVersion": self.state_version,
            "claimedAt": _format_datetime(self.claimed_at),
            "leaseExpiresAt": _format_datetime(self.lease_expires_at),
        }
        if self.manifest_sha256:
            result["manifestSha256"] = self.manifest_sha256
        if self.cleanup_reason:
            result["cleanupReason"] = self.cleanup_reason
        return result


def allowed_export_transition(source: ExportState, target: ExportState) -> None:
    """Validate one export state transition.

    Args:
        source: Current authoritative state.
        target: Requested next state.

    Raises:
        ExportStateConflict: If the transition is outside the closed v1 graph.
    """

    if target not in ALLOWED_EXPORT_TRANSITIONS.get(source, frozenset()):
        raise ExportStateConflict(
            f"Cannot transition export from {source.value} to {target.value}."
        )


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Persisted export timestamps must include a timezone.")
    return parsed.astimezone(UTC)


def _parse_optional_datetime(value: Any) -> datetime | None:
    return _parse_datetime(value) if value is not None else None
