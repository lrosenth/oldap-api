"""Purpose-authenticated internal mobile-media commit endpoint."""

from __future__ import annotations

import os
import re
from uuid import uuid4

from flask import Blueprint, Response, current_app, g, jsonify, request
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapError

from oldap_api.mobile_media.domain import (
    MobileMediaError,
    MobileMediaServiceUnavailableError,
)
from oldap_api.mobile_media.commit_lock import RedisMobileMediaCommitLock
from oldap_api.mobile_media.internal_auth import require_mobile_media_service
from oldap_api.mobile_media.repository import GraphDbMobileMediaRepository
from oldap_api.mobile_media.service import MobileMediaCommitService

internal_mobile_media_bp = Blueprint(
    "internal_mobile_media",
    __name__,
    url_prefix="/internal/mobile-media/v1/uploads",
)
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _internal_service() -> MobileMediaCommitService:
    """Build the commit service with non-token-issuing GraphDB credentials."""

    user_id = os.getenv("OLDAP_MOBILE_MEDIA_SERVICE_USER")
    password = os.getenv("OLDAP_MOBILE_MEDIA_SERVICE_PASSWORD")
    if not user_id or not password:
        raise MobileMediaServiceUnavailableError(
            "Mobile-media GraphDB service credentials are not configured."
        )
    connection = Connection(
        userId=user_id,
        credentials=password,
        context_name="DEFAULT",
        issue_access_token=False,
    )
    return MobileMediaCommitService(
        GraphDbMobileMediaRepository(connection),
        RedisMobileMediaCommitLock(),
    )


def _request_id() -> str:
    """Return one safe correlation ID without reflecting arbitrary input."""

    existing = getattr(g, "mobile_media_request_id", None)
    if existing is not None:
        return str(existing)
    supplied = request.headers.get("X-Request-ID", "")
    value = supplied if REQUEST_ID_RE.fullmatch(supplied) else str(uuid4())
    g.mobile_media_request_id = value
    return value


def _problem(error: MobileMediaError) -> Response:
    """Return the stable privacy-preserving mobile problem envelope."""

    title = {
        "validation_failed": "Mobile-media commit validation failed",
        "staging_area_not_permitted": "StagingArea is not permitted",
        "staging_upload_not_permitted": "Media creation is not permitted",
        "staging_folder_not_found": "Protected mobile inbox not found",
        "staging_folder_not_protected": "Protected mobile inbox is invalid",
        "staging_destination_changed": "Published staging destination changed",
        "client_asset_conflict": "Mobile-media identity conflicts",
        "upstream_unavailable": "OLDAP mobile-media service unavailable",
    }.get(error.code, "Mobile-media commit failed")
    response = jsonify(
        {
            "type": (
                "https://api.fasnacht.digital/problems/"
                f"{error.code.replace('_', '-')}"
            ),
            "title": title,
            "status": error.status,
            "code": error.code,
            "traceId": _request_id(),
            "retryable": error.retryable,
        }
    )
    response.status_code = error.status
    response.content_type = "application/problem+json"
    response.headers["Cache-Control"] = "no-store"
    return response


def _handle_error(error: Exception) -> Response:
    if isinstance(error, MobileMediaError):
        return _problem(error)
    if not isinstance(error, (OldapError, RuntimeError)):
        current_app.logger.exception(
            "Unexpected mobile-media commit failure requestId=%s", _request_id()
        )
    else:
        current_app.logger.error(
            "Mobile-media commit backend unavailable requestId=%s", _request_id()
        )
    return _problem(MobileMediaServiceUnavailableError())


@internal_mobile_media_bp.post("/<upload_id>/commit")
@require_mobile_media_service
def commit_mobile_media(upload_id: str):
    """Atomically create one staging medium and its permanent commit receipt."""

    try:
        result = _internal_service().commit(upload_id, request.get_json(silent=True))
    except Exception as error:
        return _handle_error(error)
    current_app.logger.info(
        "Mobile-media commit accepted uploadId=%s clientAssetId=%s requestId=%s",
        result.upload_id,
        result.client_asset_id,
        _request_id(),
    )
    response = jsonify(result.to_dict())
    response.headers["Cache-Control"] = "no-store"
    return response
