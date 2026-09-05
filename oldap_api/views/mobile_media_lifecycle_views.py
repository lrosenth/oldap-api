"""Purpose-authenticated worker transport for the mobile lifecycle outbox."""

from __future__ import annotations

import os
from uuid import uuid4

from flask import Blueprint, Response, current_app, jsonify, request
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapError

from oldap_api.mobile_media.commit_lock import RedisMobileMediaCommitLock
from oldap_api.mobile_media.domain import MobileMediaServiceUnavailableError
from oldap_api.mobile_media.internal_auth import (
    require_mobile_media_lifecycle_service,
)
from oldap_api.mobile_media.lifecycle import (
    GraphDbMobileMediaLifecycleOutbox,
    MobileMediaLifecycleError,
)

internal_mobile_media_lifecycle_bp = Blueprint(
    "internal_mobile_media_lifecycle",
    __name__,
    url_prefix="/internal/mobile-media/v1/lifecycle-events",
)


def _outbox() -> GraphDbMobileMediaLifecycleOutbox:
    user_id = os.getenv("OLDAP_MOBILE_MEDIA_SERVICE_USER")
    password = os.getenv("OLDAP_MOBILE_MEDIA_SERVICE_PASSWORD")
    if not user_id or not password:
        raise MobileMediaServiceUnavailableError(
            "Mobile-media GraphDB service credentials are not configured."
        )
    return GraphDbMobileMediaLifecycleOutbox(
        Connection(
            userId=user_id,
            credentials=password,
            context_name="DEFAULT",
            issue_access_token=False,
        )
    )


def _body(required: set[str]) -> dict[str, object]:
    value = request.get_json(silent=True)
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("Lifecycle request has invalid fields.")
    return value


def _problem(status: int, code: str, retryable: bool) -> Response:
    response = jsonify(
        {
            "type": f"https://api.fasnacht.digital/problems/{code.replace('_', '-')}",
            "title": "Mobile-media lifecycle operation failed",
            "status": status,
            "code": code,
            "traceId": str(uuid4()),
            "retryable": retryable,
        }
    )
    response.status_code = status
    response.content_type = "application/problem+json"
    response.headers["Cache-Control"] = "no-store"
    return response


@internal_mobile_media_lifecycle_bp.post("/claims")
@require_mobile_media_lifecycle_service
def claim_mobile_media_lifecycle_event():
    """Lease at most one durable lifecycle event to a media worker."""

    try:
        body = _body({"workerId"})
        worker_id = body["workerId"]
        if not isinstance(worker_id, str):
            raise ValueError("Lifecycle workerId is invalid.")
        claim = RedisMobileMediaCommitLock().run(
            lambda: _outbox().claim_next(worker_id)
        )
    except ValueError:
        return _problem(400, "validation_failed", False)
    except (MobileMediaLifecycleError, OldapError, RuntimeError):
        current_app.logger.exception("mobile_media_lifecycle_claim_failed")
        return _problem(503, "upstream_unavailable", True)
    if claim is None:
        return Response(status=204, headers={"Cache-Control": "no-store"})
    response = jsonify(claim.to_dict())
    response.headers["Cache-Control"] = "no-store"
    return response


@internal_mobile_media_lifecycle_bp.post("/<event_id>/complete")
@require_mobile_media_lifecycle_service
def complete_mobile_media_lifecycle_event(event_id: str):
    """Acknowledge one exact claim after durable media-side application."""

    try:
        body = _body({"claimId", "workerId"})
        claim_id = body["claimId"]
        worker_id = body["workerId"]
        if not isinstance(claim_id, str) or not isinstance(worker_id, str):
            raise ValueError("Lifecycle completion identity is invalid.")
        RedisMobileMediaCommitLock().run(
            lambda: _outbox().complete(event_id, claim_id, worker_id)
        )
    except ValueError:
        return _problem(400, "validation_failed", False)
    except MobileMediaLifecycleError:
        return _problem(409, "lifecycle_claim_conflict", False)
    except (OldapError, RuntimeError):
        current_app.logger.exception("mobile_media_lifecycle_completion_failed")
        return _problem(503, "upstream_unavailable", True)
    response = jsonify({"eventId": event_id, "state": "delivered"})
    response.headers["Cache-Control"] = "no-store"
    return response
