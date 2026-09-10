"""Additive, authenticated writer-recovery HTTP contract. Never controls runtimes."""

from functools import wraps
import re
from uuid import UUID, uuid4

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType
from oldap_api.authentication import authenticated_connection, require_auth
from oldap_api.writer_recovery import (
    WriterRecoveryService,
    recovery_capabilities,
    operation_summary,
)
from oldaplib.src.helpers.oldaperror import (
    OldapErrorConfiguration,
    OldapErrorNoPermission,
)
from oldaplib.src.mutation_gate import MutationGateUnavailable
from oldaplib.src.writer_recovery import RecoveryOutcomeUnknown

writer_recovery_bp = Blueprint("writer_recovery", __name__)
BASE = "/admin/writer-recovery"


@writer_recovery_bp.after_request
def private_response(response):
    """Keep operation reasons and diagnostics out of browser/shared HTTP caches."""
    response.headers["Cache-Control"] = "no-store"
    return response


def recovery_response(method):
    """Sanitize errors; uncertain writes must retain their exact request UUID."""

    @wraps(method)
    def wrapped(*args, **kwargs):
        try:
            return jsonify(method(*args, **kwargs)), 200
        except OldapErrorNoPermission:
            code, status = "FORBIDDEN", 403
        except OldapErrorConfiguration:
            code, status = "RECOVERY_DISABLED", 503
        except RequestEntityTooLarge:
            code, status = "TOO_LARGE", 413
        except (ValueError, BadRequest, UnsupportedMediaType):
            code, status = "INVALID_REQUEST", 400
        except RecoveryOutcomeUnknown:
            code, status = "RESULT_UNKNOWN", 503
        except MutationGateUnavailable:
            code, status = "RECOVERY_BLOCKED", 409
        except Exception:
            # Transport exceptions may include Redis credentials or transaction
            # addresses. Do not emit their text or traceback into HTTP/logs.
            code, status = "RESULT_UNKNOWN", 503
        return (
            jsonify(
                {
                    "code": code,
                    "message": "Recovery could not be confirmed. Refresh or retry the same operation.",
                    "requestId": str(uuid4()),
                }
            ),
            status,
        )

    return wrapped


def operation_id(value):
    """Require canonical UUIDs before looking up operation keys."""
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("Invalid operation ID")
    return value


def body(keys):
    """Accept only the documented JSON object; no runtime/evidence/actor claims."""
    request.max_content_length = 8192
    value = request.get_json()
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError("Unexpected request fields")
    return value


def with_service(method):
    """Scope the separate Redis pool to one request and close it on every path."""

    @wraps(method)
    def wrapped(*args, **kwargs):
        service = WriterRecoveryService(authenticated_connection())
        try:
            return method(service, *args, **kwargs)
        finally:
            service.recovery.client.close()

    return wrapped


@writer_recovery_bp.get(BASE + "/capabilities")
@require_auth
@recovery_response
def capabilities():
    return recovery_capabilities(authenticated_connection())


@writer_recovery_bp.get(BASE + "/status")
@require_auth
@recovery_response
@with_service
def status(service):
    value = service.status()
    result = {"state": value["state"]}
    if "revision" in value:
        result["revision"] = value["revision"]
        result["startedAt"] = value["owner"]["startedAt"]
    if "operationId" in value:
        result["operationId"] = value["operationId"]
    return result


@writer_recovery_bp.post(BASE + "/operations")
@require_auth
@recovery_response
@with_service
def begin(service):
    value = body(("operationId", "expectedRevision", "reason"))
    operation_id(value["operationId"])
    if not isinstance(value["expectedRevision"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", value["expectedRevision"]
    ):
        raise ValueError("Invalid revision")
    if (
        not isinstance(value["reason"], str)
        or not 10 <= len(value["reason"].strip()) <= 2000
    ):
        raise ValueError("Invalid reason")
    result = service.begin(
        operation_id=value["operationId"],
        expected_revision=value["expectedRevision"],
        reason=value["reason"],
    )
    return operation_summary(service, result)


@writer_recovery_bp.get(BASE + "/operations/<identifier>")
@require_auth
@recovery_response
@with_service
def operation(service, identifier):
    return operation_summary(service, service.operation(operation_id(identifier)))


@writer_recovery_bp.post(BASE + "/operations/<identifier>/finish")
@require_auth
@recovery_response
@with_service
def finish(service, identifier):
    body(())
    return operation_summary(
        service, service.finish(operation_id=operation_id(identifier))
    )
