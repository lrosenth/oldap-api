"""Public application service for project-neutral ZIP export jobs."""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from .capabilities import ExportDownloadAuthorization, ExportDownloadCapabilityIssuer
from .domain import (
    ExportJob,
    ExportKind,
    ExportProgress,
    ExportState,
    ExportVersionConflict,
)
from .profiles import ExportProfile, ExportProfileNotFoundError
from .repository import ExportJobRepository, ExportNotFoundError
from .settings import ExportOperatingPolicy
from .staging_snapshot import ExportSnapshot

PROJECT_SHORT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
QNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*:[A-Za-z_][A-Za-z0-9_.-]*$")
MAX_CURSOR_LENGTH = 512


class ExportValidationError(ValueError):
    """Raised when a public export request violates the closed contract."""

    code = "EXPORT_REQUEST_INVALID"


class ExportPermissionDeniedError(PermissionError):
    """Raised when an authenticated identity may not create exports."""

    code = "EXPORT_PERMISSION_DENIED"


class ExportProfileRegistry(Protocol):
    """Resolve the active trusted profile for a project."""

    def get_active(self, project_short_name: str) -> ExportProfile: ...


class ExportSnapshotProjector(Protocol):
    """Build one permission-filtered immutable export snapshot."""

    def project(self, connection: Any, **kwargs: Any) -> ExportSnapshot: ...


class ExportDownloadAuthorizer(Protocol):
    """Recheck frozen source visibility before capability issuance."""

    def authorize(self, connection: Any, **kwargs: Any) -> None: ...


@dataclass(frozen=True, slots=True)
class ExportJobPage:
    """One stable cursor page of caller-owned export jobs."""

    items: tuple[ExportJob, ...]
    next_cursor: str | None = None


class ExportJobService:
    """Coordinate export snapshots, ownership, persistence, and capabilities."""

    def __init__(
        self,
        repository: ExportJobRepository,
        *,
        profile_registry: ExportProfileRegistry | None = None,
        snapshot_projector: ExportSnapshotProjector | None = None,
        capability_issuer: ExportDownloadCapabilityIssuer | None = None,
        download_authorizer: ExportDownloadAuthorizer | None = None,
        operating_policy: ExportOperatingPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._profiles = profile_registry
        self._snapshot_projector = snapshot_projector
        self._capability_issuer = capability_issuer
        self._download_authorizer = download_authorizer
        self._operating_policy = (
            operating_policy or ExportOperatingPolicy.from_environment()
        )

    def estimate(
        self,
        connection: Any,
        data: Any,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Return a current read-only estimate without persisting a job."""

        request_data = _validate_create_request(data)
        _require_export_user(connection)
        profile, projector = self._snapshot_dependencies(
            request_data["projectShortName"]
        )
        snapshot = projector.project(
            connection,
            export_id=str(uuid4()),
            project_short_name=request_data["projectShortName"],
            requested_by_iri=str(connection.userIri),
            kind=request_data["kind"],
            selection_iri=request_data["selectionIri"],
            profile=profile,
            generated_at=now or datetime.now(UTC),
            enforce_size_limit=False,
        )
        return snapshot.estimate_dict()

    def create(
        self,
        connection: Any,
        data: Any,
        *,
        now: datetime | None = None,
        export_id: str | None = None,
    ) -> ExportJob:
        """Create and atomically publish one QUEUED job plus frozen manifest."""

        request_data = _validate_create_request(data)
        _require_export_user(connection)
        profile, projector = self._snapshot_dependencies(
            request_data["projectShortName"]
        )
        current = now or datetime.now(UTC)
        identifier = export_id or str(uuid4())
        _canonical_uuid(identifier, "exportId")
        snapshot = projector.project(
            connection,
            export_id=identifier,
            project_short_name=request_data["projectShortName"],
            requested_by_iri=str(connection.userIri),
            kind=request_data["kind"],
            selection_iri=request_data["selectionIri"],
            profile=profile,
            generated_at=current,
            enforce_size_limit=True,
        )
        job = ExportJob(
            export_id=identifier,
            state=ExportState.QUEUED,
            state_version=0,
            created_at=current,
            updated_at=current,
            requested_by_iri=str(connection.userIri),
            requested_by_user_id=str(connection.userid),
            selection=snapshot.selection,
            estimated_source_bytes=snapshot.source_bytes,
            warning_count=snapshot.warning_count,
            progress=ExportProgress(
                files_total=snapshot.files_total,
                bytes_total=snapshot.source_bytes,
            ),
            snapshot_at=current,
            manifest_sha256=snapshot.manifest.sha256,
        )
        self._repository.create_with_manifest(
            job,
            snapshot.manifest,
            operating_policy=self._operating_policy,
        )
        return job

    def get_for_user(self, export_id: str, connection: Any) -> ExportJob:
        """Return only an owner-visible job, hiding foreign identifiers."""

        _validate_export_id(export_id)
        job = self._repository.get(export_id)
        if job.requested_by_iri != str(connection.userIri):
            raise ExportNotFoundError("Export job not found.")
        return job

    def list_for_user(
        self,
        connection: Any,
        *,
        state: ExportState | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> ExportJobPage:
        """List caller-owned jobs through an opaque stable cursor."""

        if not 1 <= limit <= 100:
            raise ExportValidationError("limit must be between 1 and 100.")
        jobs = list(
            self._repository.list_for_user(str(connection.userIri), state=state)
        )
        start = 0
        if cursor is not None:
            key = _decode_cursor(cursor)
            try:
                start = next(
                    index + 1
                    for index, job in enumerate(jobs)
                    if (job.created_at, job.export_id) == key
                )
            except StopIteration as error:
                raise ExportValidationError(
                    "cursor does not identify a job in this result set."
                ) from error
        selected = jobs[start : start + limit + 1]
        items = tuple(selected[:limit])
        next_cursor = (
            _encode_cursor(items[-1]) if len(selected) > limit and items else None
        )
        return ExportJobPage(items=items, next_cursor=next_cursor)

    def delete(
        self,
        export_id: str,
        connection: Any,
        *,
        expected_state_version: int,
        now: datetime | None = None,
    ) -> ExportJob:
        """Cancel active work or queue artifact cleanup with optimistic locking."""

        job = self.get_for_user(export_id, connection)
        if expected_state_version != job.state_version:
            raise ExportVersionConflict("The export job changed; refresh it first.")
        target = (
            ExportState.CANCELLED
            if job.state in {ExportState.QUEUED, ExportState.BUILDING}
            else ExportState.DELETING
        )
        changes: dict[str, Any] = {}
        if target is ExportState.CANCELLED:
            changes.update(
                active_claim_id=None,
                active_claim_task=None,
                active_claim_worker_id=None,
                active_claimed_at=None,
                active_claim_lease_expires_at=None,
                active_claim_lease_seconds=None,
            )
        else:
            changes["cleanup_reason"] = (
                "READY_DELETE" if job.state is ExportState.READY else job.state.value
            )
        updated = job.transition(
            target,
            expected_state_version=expected_state_version,
            now=now,
            **changes,
        )
        self._repository.save(updated, expected_previous_version=expected_state_version)
        return updated

    def issue_download_capability(
        self,
        export_id: str,
        connection: Any,
        *,
        now: datetime | None = None,
    ) -> ExportDownloadAuthorization:
        """Reauthorize the owner and frozen sources before issuing download access."""

        job = self.get_for_user(export_id, connection)
        current = now or datetime.now(UTC)
        if not job.can_download(now=current):
            raise ValueError("Export artifact is not downloadable.")
        if self._capability_issuer is None or self._download_authorizer is None:
            raise RuntimeError("Export download service is not configured.")
        manifest = self._repository.get_manifest(export_id)
        manifest.validate_identity_for_job(job)
        self._download_authorizer.authorize(connection, job=job, manifest=manifest)
        return self._capability_issuer.issue(job, now=current)

    def _snapshot_dependencies(
        self, project_short_name: str
    ) -> tuple[ExportProfile, ExportSnapshotProjector]:
        if self._profiles is None or self._snapshot_projector is None:
            raise RuntimeError("Export snapshot service is not configured.")
        profile = self._profiles.get_active(project_short_name)
        return profile, self._snapshot_projector


def _validate_create_request(value: Any) -> dict[str, Any]:
    allowed = {"projectShortName", "kind", "selectionIri", "includeTrash"}
    if (
        not isinstance(value, dict)
        or not {"projectShortName", "kind"} <= set(value)
        or not set(value) <= allowed
    ):
        raise ExportValidationError(
            "Exactly projectShortName, kind, optional selectionIri, and optional includeTrash are allowed."
        )
    project = value["projectShortName"]
    if not isinstance(project, str) or PROJECT_SHORT_NAME_RE.fullmatch(project) is None:
        raise ExportValidationError("projectShortName is invalid.")
    try:
        kind = ExportKind(value["kind"])
    except (TypeError, ValueError) as error:
        raise ExportValidationError("kind is invalid.") from error
    include_trash = value.get("includeTrash", False)
    if include_trash is not False:
        raise ExportValidationError("includeTrash must be false.")
    selection = value.get("selectionIri")
    requires_selection = kind is not ExportKind.ARCHIVE_ALL
    if requires_selection:
        selection = _validate_iri(selection, "selectionIri")
    elif selection is not None:
        raise ExportValidationError("selectionIri is forbidden for ARCHIVE_ALL.")
    return {
        "projectShortName": project,
        "kind": kind,
        "selectionIri": selection,
    }


def _require_export_user(connection: Any) -> None:
    user_id = str(getattr(connection, "userid", ""))
    user_iri = str(getattr(connection, "userIri", ""))
    if not user_id or not user_iri or user_id.casefold() == "unknown":
        raise ExportPermissionDeniedError("The anonymous user may not create exports.")


def _validate_iri(value: Any, field: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 2048:
        raise ExportValidationError(f"{field} must be an absolute IRI.")
    if any(character in value for character in '<>"{}|\\^`\x00\r\n'):
        raise ExportValidationError(f"{field} contains unsafe characters.")
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    prefix = "urn:uuid:"
    if value.startswith(prefix):
        identifier = value[len(prefix) :]
        try:
            parsed_uuid = UUID(identifier)
        except (AttributeError, ValueError):
            pass
        else:
            if identifier == str(parsed_uuid):
                return value
    if QNAME_RE.fullmatch(value):
        return value
    raise ExportValidationError(
        f"{field} must be an absolute HTTP(S) IRI, canonical UUID URN, or OLDAP QName."
    )


def _validate_export_id(value: str) -> None:
    try:
        _canonical_uuid(value, "exportId")
    except ExportValidationError as error:
        raise ExportNotFoundError("Export job not found.") from error


def _canonical_uuid(value: Any, field: str) -> str:
    try:
        parsed = UUID(str(value))
    except (TypeError, ValueError, AttributeError) as error:
        raise ExportValidationError(f"{field} must be a canonical UUID.") from error
    canonical = str(parsed)
    if value != canonical:
        raise ExportValidationError(f"{field} must be a canonical UUID.")
    return canonical


def _encode_cursor(job: ExportJob) -> str:
    payload = json.dumps(
        {
            "createdAt": job.created_at.astimezone(UTC).isoformat(),
            "exportId": job.export_id,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    if not cursor or len(cursor) > MAX_CURSOR_LENGTH or not cursor.isascii():
        raise ExportValidationError("cursor is invalid.")
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict) or set(value) != {"createdAt", "exportId"}:
            raise ValueError
        created_at = datetime.fromisoformat(str(value["createdAt"]))
        if created_at.tzinfo is None:
            raise ValueError
        export_id = _canonical_uuid(value["exportId"], "exportId")
    except (
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        ExportValidationError,
    ) as error:
        raise ExportValidationError("cursor is invalid.") from error
    return created_at.astimezone(UTC), export_id


__all__ = [
    "ExportJobPage",
    "ExportJobService",
    "ExportPermissionDeniedError",
    "ExportProfileNotFoundError",
    "ExportValidationError",
]
