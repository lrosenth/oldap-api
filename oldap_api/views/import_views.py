"""Public project-neutral ZIP import job endpoints."""

from __future__ import annotations

import re
from uuid import uuid4

from flask import Blueprint, Response, current_app, g, jsonify, request
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapError

from oldap_api.authentication import authenticated_connection, require_auth
from oldap_api.imports.authorization import (
    ImportPermissionDeniedError,
    ImportQuotaNotConfiguredError,
    ImportTargetNotFoundError,
    OldapImportAuthorizer,
    OldapImportTargetInspector,
)
from oldap_api.imports.capabilities import UploadCapabilityIssuer
from oldap_api.imports.audit import log_import_event
from oldap_api.imports.internal_auth import require_import_service
from oldap_api.imports.domain import (
    ImportDomainError,
    ImportState,
    NotificationStatus,
)
from oldap_api.imports.repository import (
    GraphDbImportJobRepository,
    ImportNotFoundError,
    ImportQuotaExceededError,
)
from oldap_api.imports.service import (
    ImportJobService,
    ImportPayloadTooLargeError,
    ImportValidationError,
)
from oldap_api.imports.records import (
    ImportRecordClient,
    ImportRecordUnavailableError,
    ImportReportNotReadyError,
)
from oldap_api.imports.notifications import deliver_import_notification
from oldap_api.staging_area import (
    StagingAreaServiceUnavailable,
    run_staging_mutation,
)

import_bp = Blueprint("imports", __name__, url_prefix="/imports")
internal_import_bp = Blueprint(
    "internal_imports", __name__, url_prefix="/internal/imports"
)
internal_claim_bp = Blueprint(
    "internal_import_claims", __name__, url_prefix="/internal/import-claims"
)
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _service(connection) -> ImportJobService:
    """Build the request-scoped service around the authenticated connection."""
    return ImportJobService(
        GraphDbImportJobRepository(connection),
        OldapImportAuthorizer(),
        UploadCapabilityIssuer(),
        OldapImportTargetInspector(connection),
    )


def _internal_service() -> ImportJobService:
    """Build a service with dedicated non-token GraphDB credentials."""
    return _service(_import_service_connection())


def _import_service_connection():
    """Create the dedicated non-token-issuing OLDAP service connection."""
    import os

    user_id = os.getenv("OLDAP_IMPORT_SERVICE_USER")
    password = os.getenv("OLDAP_IMPORT_SERVICE_PASSWORD")
    if not user_id or not password:
        raise RuntimeError(
            "OLDAP_IMPORT_SERVICE_USER and OLDAP_IMPORT_SERVICE_PASSWORD must be configured."
        )
    return Connection(
        userId=user_id,
        credentials=password,
        context_name="DEFAULT",
        issue_access_token=False,
    )


def _record_client() -> ImportRecordClient:
    """Build the purpose-specific API-to-media retained-record client."""
    return ImportRecordClient()


def _deliver_notification(job) -> None:
    """Resolve and deliver import mail with the dedicated service identity."""
    deliver_import_notification(_import_service_connection(), job)


def _error(status: int, code: str, message: str) -> Response:
    """Return the stable ZIP-import error envelope."""
    response = jsonify(
        {
            "code": code,
            "message": message[:500],
            "requestId": _request_id(),
        }
    )
    response.status_code = status
    if status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return response


def _request_id() -> str:
    """Return one sanitized correlation ID shared by audit and error output."""
    existing = getattr(g, "import_request_id", None)
    if existing is not None:
        return existing
    supplied = request.headers.get("X-Request-ID", "")
    value = supplied if REQUEST_ID_RE.fullmatch(supplied) else str(uuid4())
    g.import_request_id = value
    return value


def _handle_error(error: Exception) -> Response:
    if isinstance(error, StagingAreaServiceUnavailable):
        return _error(503, "IMPORT_SERVICE_UNAVAILABLE", "Import service unavailable.")
    if isinstance(error, ImportNotFoundError):
        return _error(404, error.code, str(error))
    if isinstance(error, ImportPermissionDeniedError):
        return _error(403, error.code, str(error))
    if isinstance(error, ImportTargetNotFoundError):
        return _error(404, error.code, str(error))
    if isinstance(error, ImportQuotaExceededError):
        return _error(409, error.code, str(error))
    if isinstance(error, ImportQuotaNotConfiguredError):
        return _error(503, error.code, str(error))
    if isinstance(error, ImportDomainError):
        return _error(409, error.code, str(error))
    if isinstance(error, ImportPayloadTooLargeError):
        return _error(413, error.code, str(error))
    if isinstance(error, ImportReportNotReadyError):
        return _error(409, error.code, str(error))
    if isinstance(error, ImportRecordUnavailableError):
        return _error(503, error.code, str(error))
    if isinstance(error, ImportValidationError):
        return _error(400, error.code, str(error))
    if isinstance(error, (OldapError, RuntimeError)):
        return _error(503, "IMPORT_SERVICE_UNAVAILABLE", "Import service unavailable.")
    raise error


def _expected_version() -> int:
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"expectedStateVersion"}:
        raise ImportValidationError("Exactly expectedStateVersion is required.")
    version = data["expectedStateVersion"]
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise ImportValidationError(
            "expectedStateVersion must be a non-negative integer."
        )
    return version


@import_bp.post("")
@require_auth
def create_import_job():
    """Create one immutable-target UPLOADING job and upload capability."""
    connection = authenticated_connection()
    try:
        job, upload = _service(connection).create(
            connection, request.get_json(silent=True)
        )
    except Exception as error:
        return _handle_error(error)
    log_import_event(current_app.logger, "created", job, request_id=_request_id())
    response = jsonify({"job": job.to_dict(), "upload": upload.to_dict()})
    response.status_code = 201
    response.headers["Cache-Control"] = "no-store"
    return response


@import_bp.get("")
@require_auth
def list_import_jobs():
    """List the caller's import jobs newest first."""
    connection = authenticated_connection()
    try:
        if not set(request.args) <= {"state", "cursor", "limit"}:
            raise ImportValidationError("Unknown list query parameter.")
        raw_state = request.args.get("state")
        state = ImportState(raw_state) if raw_state else None
        raw_limit = request.args.get("limit", "25")
        limit = int(raw_limit)
        page = _service(connection).list_for_user(
            connection,
            state=state,
            cursor=request.args.get("cursor"),
            limit=limit,
        )
    except (ValueError, TypeError) as error:
        return _error(400, "IMPORT_REQUEST_INVALID", str(error))
    except Exception as error:
        return _handle_error(error)
    result = {"items": [job.to_dict() for job in page.items]}
    if page.next_cursor is not None:
        result["nextCursor"] = page.next_cursor
    return jsonify(result)


@import_bp.get("/<import_id>")
@require_auth
def get_import_job(import_id: str):
    """Read one caller-owned job and expose its optimistic ETag."""
    connection = authenticated_connection()
    try:
        job = _service(connection).get_for_user(import_id, connection)
    except Exception as error:
        return _handle_error(error)
    response = jsonify(job.to_dict())
    response.headers["ETag"] = f'"{job.state_version}"'
    return response


@import_bp.get("/<import_id>/report")
@require_auth
def get_import_report(import_id: str):
    """Authorize and checksum-verify a protected retained report."""
    connection = authenticated_connection()
    try:
        job = _service(connection).get_for_user(import_id, connection)
        report = _record_client().get_report(job)
    except Exception as error:
        return _handle_error(error)
    response = jsonify(report)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@import_bp.post("/<import_id>/upload-capability")
@require_auth
def issue_upload_capability(import_id: str):
    """Reissue upload access while an unchanged job remains UPLOADING."""
    connection = authenticated_connection()
    try:
        upload = _service(connection).reissue_upload_capability(
            import_id,
            connection,
            expected_state_version=_expected_version(),
        )
    except Exception as error:
        return _handle_error(error)
    response = jsonify(upload.to_dict())
    response.headers["Cache-Control"] = "no-store"
    return response


@import_bp.post("/<import_id>/cancel")
@require_auth
def cancel_import_job(import_id: str):
    """Cancel UPLOADING/READY and queue idempotent payload cleanup."""
    connection = authenticated_connection()
    try:
        job = _service(connection).cancel(
            import_id,
            connection,
            expected_state_version=_expected_version(),
        )
    except Exception as error:
        return _handle_error(error)
    log_import_event(current_app.logger, "cancelled", job, request_id=_request_id())
    return jsonify(job.to_dict()), 202


@import_bp.post("/<import_id>/confirm")
@require_auth
def confirm_import_job(import_id: str):
    """Reauthorize and atomically move an unexpired READY job to IMPORTING."""
    connection = authenticated_connection()
    try:
        job = _service(connection).confirm(
            import_id,
            connection,
            expected_state_version=_expected_version(),
        )
    except Exception as error:
        return _handle_error(error)
    log_import_event(
        current_app.logger, "import_requested", job, request_id=_request_id()
    )
    return jsonify(job.to_dict()), 202


@internal_import_bp.post("/<import_id>/sip-stored")
@require_import_service
def record_stored_sip(import_id: str):
    """Idempotently record a finalized SIP and queue validation."""
    try:
        job = _internal_service().record_sip_stored(
            import_id, request.get_json(silent=True)
        )
    except Exception as error:
        return _handle_error(error)
    log_import_event(current_app.logger, "sip_stored", job, request_id=_request_id())
    return jsonify(job.to_dict())


@internal_claim_bp.post("")
@require_import_service
def claim_next_import_task():
    """Atomically lease at most one task to the sequential worker."""
    try:
        service = _internal_service()
        claim = service.claim_next(request.get_json(silent=True))
    except Exception as error:
        return _handle_error(error)
    if claim is None:
        _reconcile_one_notification(service)
        return "", 204
    return jsonify(claim.to_dict())


def _reconcile_one_notification(service: ImportJobService) -> None:
    """Retry one due API-owned email without blocking the ingest queue."""

    try:
        job = service.next_notification_retry()
        if job is not None:
            _attempt_notification(service, job)
    except Exception as error:
        current_app.logger.warning(
            "Import notification reconciliation failed (%s).",
            type(error).__name__,
        )


@internal_claim_bp.post("/<claim_id>/heartbeat")
@require_import_service
def heartbeat_import_claim(claim_id: str):
    """Renew an active lease without mutating the import lifecycle state."""
    try:
        accepted_id, lease_expires_at = _internal_service().heartbeat_claim(
            claim_id, request.get_json(silent=True)
        )
    except Exception as error:
        return _handle_error(error)
    return jsonify(
        {
            "claimId": accepted_id,
            "leaseExpiresAt": lease_expires_at.isoformat().replace("+00:00", "Z"),
        }
    )


@internal_claim_bp.post("/<claim_id>/target-preflight")
@require_import_service
def preflight_import_target(claim_id: str):
    """Return bounded collision findings for one leased ZIP root inventory."""

    try:
        result = _internal_service().preflight_target(
            claim_id, request.get_json(silent=True)
        )
    except Exception as error:
        return _handle_error(error)
    return jsonify(result)


@internal_import_bp.post("/<import_id>/validation-result")
@require_import_service
def record_import_validation_result(import_id: str):
    """Publish an idempotent validation outcome and reconcile reserved quota."""
    try:
        service = _internal_service()
        job = service.record_validation_result(import_id, request.get_json(silent=True))
        job = _attempt_notification(service, job)
    except Exception as error:
        return _handle_error(error)
    log_import_event(
        current_app.logger, "validation_recorded", job, request_id=_request_id()
    )
    return jsonify(job.to_dict())


@internal_import_bp.post("/<import_id>/commit")
@require_import_service
def commit_staging_import(import_id: str):
    """Atomically create the complete staging hierarchy and finish IMPORT."""

    try:
        service = _internal_service()
        payload = request.get_json(silent=True)
        job, event_id, resources = run_staging_mutation(
            "shared:StagingMediaObject",
            lambda: service.commit_import(import_id, payload),
        )
        job = _attempt_notification(service, job)
    except Exception as error:
        return _handle_error(error)
    log_import_event(
        current_app.logger, "import_committed", job, request_id=_request_id()
    )
    return jsonify({"eventId": event_id, "job": job.to_dict(), "resources": resources})


@internal_import_bp.post("/<import_id>/failed")
@require_import_service
def fail_staging_import(import_id: str):
    """Record terminal IMPORT failure after compensation and payload deletion."""

    try:
        service = _internal_service()
        job = service.fail_import(import_id, request.get_json(silent=True))
        job = _attempt_notification(service, job)
    except Exception as error:
        return _handle_error(error)
    log_import_event(current_app.logger, "import_failed", job, request_id=_request_id())
    return jsonify(job.to_dict())


@internal_import_bp.post("/<import_id>/cleanup-result")
@require_import_service
def complete_import_cleanup(import_id: str):
    """Accept deletion proof and finalize one API-selected CLEANUP task."""

    try:
        job = _internal_service().record_cleanup_result(
            import_id, request.get_json(silent=True)
        )
    except Exception as error:
        return _handle_error(error)
    log_import_event(
        current_app.logger, "import_cleanup_completed", job, request_id=_request_id()
    )
    return jsonify(job.to_dict())


def _attempt_notification(service: ImportJobService, job):
    """Attempt bounded mail submission after durable lifecycle commit."""
    if (
        job.notification_status
        not in {NotificationStatus.PENDING, NotificationStatus.FAILED}
        or job.notification_attempts >= 3
    ):
        return job
    try:
        _deliver_notification(job)
    except Exception as error:
        current_app.logger.error(
            "Import notification submission failed for %s (%s).",
            job.import_id,
            type(error).__name__,
        )
        return service.record_notification_result(
            job.import_id, success=False, error=type(error).__name__
        )
    return service.record_notification_result(job.import_id, success=True)
