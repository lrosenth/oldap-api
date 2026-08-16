"""Public project-neutral ZIP export endpoints."""

from __future__ import annotations

import base64
import os
import re
from uuid import uuid4

from flask import Blueprint, Response, current_app, g, jsonify, request
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapError

from oldap_api.authentication import authenticated_connection, require_auth
from oldap_api.exports.capabilities import ExportDownloadCapabilityIssuer
from oldap_api.exports.archive_snapshot import (
    ArchiveDownloadAuthorizer,
    ArchiveSnapshotProjector,
    OldapArchiveInventoryReader,
)
from oldap_api.exports.domain import (
    ExportNotificationStatus,
    ExportState,
    ExportStateConflict,
    ExportVersionConflict,
)
from oldap_api.exports.manifest import ExportManifestError
from oldap_api.exports.internal_auth import require_export_service
from oldap_api.exports.notifications import deliver_export_notification
from oldap_api.exports.media_sources import (
    ExportSourceUnavailableError,
    MediaBinarySourceResolver,
)
from oldap_api.exports.profiles import (
    ExportProfileError,
    ExportProfileNotFoundError,
    FileExportProfileRegistry,
)
from oldap_api.exports.repository import (
    ExportAlreadyExistsError,
    ExportNotFoundError,
    ExportQuotaExceededError,
    ExportRepositoryConflict,
    GraphDbExportJobRepository,
)
from oldap_api.exports.service import (
    ExportJobService,
    ExportPermissionDeniedError,
    ExportValidationError,
)
from oldap_api.exports.snapshot_router import (
    ExportDownloadAuthorizerRouter,
    ExportSnapshotRouter,
)
from oldap_api.exports.settings import ExportOperatingPolicy
from oldap_api.exports.staging_snapshot import (
    ExportDownloadPermissionError,
    ExportSelectionNotFoundError,
    ExportSizeLimitError,
    ExportSnapshotError,
    OldapStagingInventoryReader,
    StagingDownloadAuthorizer,
    StagingSnapshotProjector,
)
from oldap_api.exports.worker_service import (
    ExportClaimConflict,
    ExportEventConflict,
    ExportWorkerService,
    ExportWorkerValidationError,
)

export_bp = Blueprint("exports", __name__, url_prefix="/exports")
internal_export_bp = Blueprint(
    "internal_exports", __name__, url_prefix="/internal/exports"
)
internal_export_claim_bp = Blueprint(
    "internal_export_claims", __name__, url_prefix="/internal/export-claims"
)
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _service(
    connection,
    *,
    snapshots: bool = False,
    downloads: bool = False,
) -> ExportJobService:
    """Compose only the dependencies needed by the current public operation."""

    policy = ExportOperatingPolicy.from_environment()
    options = {"operating_policy": policy}
    if snapshots:
        registry = FileExportProfileRegistry.from_environment()
        archive_reader = OldapArchiveInventoryReader()
        options.update(
            profile_registry=registry,
            snapshot_projector=ExportSnapshotRouter(
                StagingSnapshotProjector(
                    OldapStagingInventoryReader(),
                    MediaBinarySourceResolver(),
                    max_archive_bytes=policy.max_archive_bytes,
                ),
                ArchiveSnapshotProjector(
                    archive_reader,
                    MediaBinarySourceResolver(),
                    max_archive_bytes=policy.max_archive_bytes,
                ),
            ),
        )
    if downloads:
        registry = FileExportProfileRegistry.from_environment()
        options.update(
            capability_issuer=ExportDownloadCapabilityIssuer(),
            download_authorizer=ExportDownloadAuthorizerRouter(
                StagingDownloadAuthorizer(OldapStagingInventoryReader()),
                ArchiveDownloadAuthorizer(OldapArchiveInventoryReader(), registry),
            ),
        )
    return ExportJobService(GraphDbExportJobRepository(connection), **options)


def _internal_service() -> ExportWorkerService:
    """Build the worker service with non-token-issuing OLDAP credentials."""

    return ExportWorkerService(
        GraphDbExportJobRepository(_export_service_connection()),
        operating_policy=ExportOperatingPolicy.from_environment(),
    )


def _export_service_connection() -> Connection:
    """Open the restricted non-token-issuing export service connection."""

    user_id = os.getenv("OLDAP_EXPORT_SERVICE_USER")
    password = os.getenv("OLDAP_EXPORT_SERVICE_PASSWORD")
    if not user_id or not password:
        raise RuntimeError(
            "OLDAP_EXPORT_SERVICE_USER and OLDAP_EXPORT_SERVICE_PASSWORD must be configured."
        )
    return Connection(
        userId=user_id,
        credentials=password,
        context_name="DEFAULT",
        issue_access_token=False,
    )


def _deliver_notification(job) -> None:
    """Resolve and deliver export mail through the restricted service identity."""

    deliver_export_notification(_export_service_connection(), job)


def _error(status: int, code: str, message: str) -> Response:
    """Return the stable ZIP-export error envelope without internal details."""

    response = jsonify(
        {"code": code, "message": message[:500], "requestId": _request_id()}
    )
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    if status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return response


def _request_id() -> str:
    existing = getattr(g, "export_request_id", None)
    if existing is not None:
        return existing
    supplied = request.headers.get("X-Request-ID", "")
    value = supplied if REQUEST_ID_RE.fullmatch(supplied) else str(uuid4())
    g.export_request_id = value
    return value


def _handle_error(error: Exception) -> Response:
    if isinstance(error, ExportWorkerValidationError):
        return _error(400, "EXPORT_REQUEST_INVALID", str(error))
    if isinstance(error, ExportValidationError):
        return _error(400, error.code, str(error))
    if isinstance(error, ExportPermissionDeniedError):
        return _error(403, error.code, str(error))
    if isinstance(error, ExportDownloadPermissionError):
        return _error(403, "EXPORT_PERMISSION_DENIED", str(error))
    if isinstance(error, ExportProfileNotFoundError):
        return _error(404, "EXPORT_PROFILE_NOT_FOUND", str(error))
    if isinstance(error, (ExportNotFoundError, ExportSelectionNotFoundError)):
        return _error(404, "EXPORT_NOT_FOUND", "Export or selection not found.")
    if isinstance(error, ExportSizeLimitError):
        return _error(413, "EXPORT_SIZE_LIMIT", str(error))
    if isinstance(error, ExportQuotaExceededError):
        return _error(429, "EXPORT_QUOTA_EXCEEDED", str(error))
    if isinstance(
        error,
        (
            ExportClaimConflict,
            ExportEventConflict,
            ExportStateConflict,
            ExportVersionConflict,
            ExportRepositoryConflict,
            ExportAlreadyExistsError,
        ),
    ):
        return _error(409, "EXPORT_STATE_CONFLICT", str(error))
    if isinstance(error, ExportSourceUnavailableError):
        return _error(503, "EXPORT_SOURCE_UNAVAILABLE", str(error))
    if isinstance(
        error,
        (ExportProfileError, ExportManifestError, OldapError, RuntimeError),
    ):
        current_app.logger.error("Export service failure: %s", type(error).__name__)
        return _error(503, "EXPORT_SERVICE_UNAVAILABLE", "Export service unavailable.")
    if isinstance(error, ExportSnapshotError):
        return _error(409, "EXPORT_SNAPSHOT_CONFLICT", str(error))
    if isinstance(error, ValueError):
        return _error(409, "EXPORT_STATE_CONFLICT", str(error))
    raise error


@export_bp.post("/estimate")
@require_auth
def estimate_export():
    """Estimate one caller-visible Staging or Archive selection."""

    connection = authenticated_connection()
    try:
        estimate = _service(connection, snapshots=True).estimate(
            connection, request.get_json(silent=True)
        )
    except Exception as error:
        return _handle_error(error)
    response = jsonify(estimate)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@export_bp.post("")
@require_auth
def create_export():
    """Freeze one authorized Staging or Archive snapshot and queue its ZIP."""

    connection = authenticated_connection()
    try:
        job = _service(connection, snapshots=True).create(
            connection, request.get_json(silent=True)
        )
    except Exception as error:
        return _handle_error(error)
    current_app.logger.info(
        "export_created exportId=%s owner=%s requestId=%s",
        job.export_id,
        job.requested_by_iri,
        _request_id(),
    )
    response = jsonify(job.to_dict())
    response.status_code = 202
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Location"] = f"/exports/{job.export_id}"
    return response


@export_bp.get("")
@require_auth
def list_exports():
    """List only the caller's export jobs newest first."""

    connection = authenticated_connection()
    try:
        if not set(request.args) <= {"state", "cursor", "limit"}:
            raise ExportValidationError("Unknown list query parameter.")
        raw_state = request.args.get("state")
        state = ExportState(raw_state) if raw_state else None
        limit = int(request.args.get("limit", "25"))
        page = _service(connection).list_for_user(
            connection,
            state=state,
            cursor=request.args.get("cursor"),
            limit=limit,
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, ExportValidationError):
            return _handle_error(error)
        return _error(400, "EXPORT_REQUEST_INVALID", str(error))
    except Exception as error:
        return _handle_error(error)
    result = {"items": [job.to_dict() for job in page.items]}
    if page.next_cursor is not None:
        result["nextCursor"] = page.next_cursor
    response = jsonify(result)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@export_bp.get("/<export_id>")
@require_auth
def get_export(export_id: str):
    """Read one caller-owned export job with its optimistic ETag."""

    connection = authenticated_connection()
    try:
        job = _service(connection).get_for_user(export_id, connection)
    except Exception as error:
        return _handle_error(error)
    response = jsonify(job.to_dict())
    response.headers["ETag"] = f'"{job.state_version}"'
    response.headers["Cache-Control"] = "private, no-store"
    return response


@export_bp.delete("/<export_id>")
@require_auth
def delete_export(export_id: str):
    """Cancel active work or queue cleanup of an existing artifact."""

    connection = authenticated_connection()
    try:
        if set(request.args) != {"expectedStateVersion"}:
            raise ExportValidationError("Exactly expectedStateVersion is required.")
        expected = int(request.args["expectedStateVersion"])
        if expected < 0:
            raise ExportValidationError("expectedStateVersion must be non-negative.")
    except (TypeError, ValueError) as error:
        if isinstance(error, ExportValidationError):
            return _handle_error(error)
        return _error(400, "EXPORT_REQUEST_INVALID", str(error))
    try:
        job = _service(connection).delete(
            export_id,
            connection,
            expected_state_version=expected,
        )
    except Exception as error:
        return _handle_error(error)
    current_app.logger.info(
        "export_delete_requested exportId=%s state=%s requestId=%s",
        job.export_id,
        job.state.value,
        _request_id(),
    )
    response = jsonify(job.to_dict())
    response.headers["Cache-Control"] = "private, no-store"
    return response


@export_bp.post("/<export_id>/download-capability")
@require_auth
def issue_export_download(export_id: str):
    """Reauthorize a READY artifact and issue one short-lived download URL."""

    connection = authenticated_connection()
    try:
        authorization = _service(connection, downloads=True).issue_download_capability(
            export_id, connection
        )
    except Exception as error:
        return _handle_error(error)
    response = jsonify(authorization.to_dict())
    response.headers["Cache-Control"] = "no-store"
    return response


@internal_export_claim_bp.post("")
@require_export_service
def claim_export_task():
    """Atomically lease the next supported BUILD or CLEANUP task."""

    try:
        service = _internal_service()
        claim = service.claim_next(request.get_json(silent=True))
    except Exception as error:
        return _handle_error(error)
    if claim is None:
        _reconcile_one_notification(service)
    response = jsonify(claim.to_dict() if claim is not None else None)
    response.headers["Cache-Control"] = "no-store"
    return response


@internal_export_claim_bp.post("/<claim_id>/heartbeat")
@require_export_service
def heartbeat_export_claim(claim_id: str):
    """Renew an active worker lease without advancing lifecycle stateVersion."""

    try:
        accepted_id, lease_expires_at = _internal_service().heartbeat_claim(
            claim_id, request.get_json(silent=True)
        )
    except Exception as error:
        return _handle_error(error)
    response = jsonify(
        {
            "claimId": accepted_id,
            "leaseExpiresAt": lease_expires_at.isoformat().replace("+00:00", "Z"),
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@internal_export_bp.get("/<export_id>/manifest")
@require_export_service
def get_export_manifest(export_id: str):
    """Return canonical manifest bytes for the current BUILD claim only."""

    try:
        if set(request.args) != {"claimId"}:
            raise ExportWorkerValidationError("Exactly claimId is required.")
        manifest = _internal_service().manifest_for_claim(
            export_id, request.args["claimId"]
        )
    except Exception as error:
        return _handle_error(error)
    digest = base64.b64encode(bytes.fromhex(manifest.sha256)).decode("ascii")
    response = Response(manifest.canonical_json, content_type="application/json")
    response.headers["Digest"] = f"sha-256={digest}"
    response.headers["Cache-Control"] = "private, no-store"
    return response


@internal_export_bp.post("/<export_id>/result")
@require_export_service
def record_export_result(export_id: str):
    """Publish one idempotent READY or FAILED BUILD outcome."""

    try:
        service = _internal_service()
        job = service.record_build_result(export_id, request.get_json(silent=True))
        job = _attempt_notification(service, job)
    except Exception as error:
        return _handle_error(error)
    response = jsonify(job.to_dict())
    response.headers["Cache-Control"] = "no-store"
    return response


def _reconcile_one_notification(service: ExportWorkerService) -> None:
    """Retry one due API-owned email without blocking the export queue."""

    try:
        job = service.next_notification_retry()
        if job is not None:
            _attempt_notification(service, job)
    except Exception as error:
        current_app.logger.warning(
            "Export notification reconciliation failed (%s).",
            type(error).__name__,
        )


def _attempt_notification(service: ExportWorkerService, job):
    """Attempt bounded mail submission after durable lifecycle commit."""

    if (
        job.notification_status
        not in {ExportNotificationStatus.PENDING, ExportNotificationStatus.FAILED}
        or job.notification_attempts >= 3
    ):
        return job
    try:
        _deliver_notification(job)
    except Exception as error:
        current_app.logger.error(
            "Export notification submission failed for %s (%s).",
            job.export_id,
            type(error).__name__,
        )
        return service.record_notification_result(
            job.export_id, success=False, error=type(error).__name__
        )
    return service.record_notification_result(job.export_id, success=True)


@internal_export_bp.post("/<export_id>/cleanup-result")
@require_export_service
def record_export_cleanup_result(export_id: str):
    """Accept deletion proof and atomically purge the frozen manifest."""

    try:
        job = _internal_service().record_cleanup_result(
            export_id, request.get_json(silent=True)
        )
    except Exception as error:
        return _handle_error(error)
    response = jsonify(job.to_dict())
    response.headers["Cache-Control"] = "no-store"
    return response
