"""Additive v1 archive adoption, capabilities, mixed inventory, moves and receipts."""

from functools import wraps
from uuid import uuid4
from flask import Blueprint, jsonify, request, current_app
from werkzeug.exceptions import RequestEntityTooLarge

from oldap_api.authentication import authenticated_connection, require_auth
from oldaplib.src.archive_policy import ArchiveConflict, ArchivePolicy
from oldaplib.src.archive_repository import ArchiveRepository
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.oldaperror import (
    OldapErrorConfiguration,
    OldapErrorNoPermission,
    OldapErrorNotFound,
    OldapErrorValue,
    OldapErrorInUse,
    OldapErrorInconsistency,
)
from oldaplib.src.mutation_gate import MutationGateUnavailable
from oldaplib.src.xsd.iri import Iri

archive_structure_bp = Blueprint("archive_structure", __name__)
MAX_REQUEST_BYTES = 2_000_000


@archive_structure_bp.after_request
def private_response(response):
    """Capabilities and operation receipts must not enter shared caches."""
    response.headers["Cache-Control"] = "no-store"
    return response


def domain_response(method):
    """Keep the frozen error envelope on additive routes only."""

    @wraps(method)
    def respond(*args, **kwargs):
        request_id = str(uuid4())
        try:
            return jsonify(method(*args, **kwargs)), 200
        except RequestEntityTooLarge:
            code, message, status = (
                "TOO_LARGE",
                "The archive request is too large.",
                413,
            )
        except (MutationGateUnavailable, OldapErrorConfiguration):
            code, message, status = (
                "COORDINATION_UNAVAILABLE",
                "Archive coordination or configuration is unavailable.",
                503,
            )
        except OldapErrorNoPermission:
            code, message, status = "FORBIDDEN", "The operation is not permitted.", 403
        except OldapErrorNotFound:
            code, message, status = (
                "NOT_FOUND",
                "The resource or operation was not found.",
                404,
            )
        except OldapErrorInUse:
            code, message, status = (
                "REFERENCE_IN_USE",
                "The resource is still referenced.",
                409,
            )
        except ArchiveConflict as error:
            code, message = error.code, str(error)
            status = 400 if code == "INVALID_HIERARCHY" else error.status
        except OldapErrorInconsistency:
            code, message, status = (
                "INVALID_HIERARCHY",
                "The folder hierarchy is inconsistent.",
                400,
            )
        except OldapErrorValue as error:
            code, message, status = "INVALID_REQUEST", str(error), 400
        except Exception:
            # Transport failures must keep the same retry/receipt contract as
            # domain failures, without exposing backend details to the caller.
            current_app.logger.exception("Archive operation failed (%s).", request_id)
            code, message, status = (
                "COORDINATION_UNAVAILABLE",
                "The archive operation could not be confirmed.",
                503,
            )
        return (
            jsonify({"code": code, "message": message[:500], "requestId": request_id}),
            status,
        )

    return respond


@archive_structure_bp.get("/archive/<project>/structure/capabilities")
@require_auth
@domain_response
def capabilities(project):
    """Report project policy and caller capabilities without granting instance rights."""
    connection = authenticated_connection()
    policy = ArchivePolicy.load(connection, project)
    can_manage = policy.enabled and policy.has_role(policy.structure_roles)
    actor = connection.userdata
    system = actor.inProject.get(Iri("oldap:SystemProject")) or ()
    permissions = actor.inProject.get(policy.project.projectIri) or ()
    can_create = can_manage and (
        AdminPermission.ADMIN_OLDAP in system
        or AdminPermission.ADMIN_CREATE in permissions
    )
    return {
        "enabled": policy.enabled,
        "canManageStructure": bool(can_manage),
        "canCreateUnits": bool(can_create),
        "maxSourceFolders": 5000,
        "maxMutations": 500,
        "maxRequestBytes": MAX_REQUEST_BYTES,
    }


@archive_structure_bp.post("/data/<project>/staging-reference-move")
@require_auth
@domain_response
def move_reference(project):
    """Apply or exactly replay an authorised, revision-checked reference move."""
    request.max_content_length = MAX_REQUEST_BYTES
    if not request.is_json:
        raise OldapErrorValue("JSON is required.")
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise OldapErrorValue("Request body must be an object.")
    return ArchiveRepository(authenticated_connection(), project).move_reference(
        body, operation_id=request.headers.get("Idempotency-Key")
    )


@archive_structure_bp.get("/archive/<project>/structure/operations/<operation_id>")
@require_auth
@domain_response
def operation(project, operation_id):
    """Return only a currently visible receipt scoped to the authenticated owner."""
    return ArchiveRepository(authenticated_connection(), project).operation(
        operation_id
    )


@archive_structure_bp.get("/data/<project>/staging-folder-inventory")
@require_auth
@domain_response
def folder_inventory(project):
    """Expose signed, permission-filtered pages without changing legacy search."""
    import hashlib
    from oldaplib.src.archive_inventory import ArchiveInventory
    from oldaplib.src.authentication import TokenSettings

    if not set(request.args) <= {"folderIri", "limit", "cursor"} or any(
        len(request.args.getlist(k)) != 1 for k in request.args
    ):
        raise OldapErrorValue("Invalid inventory query parameters.")
    raw_limit = request.args.get("limit", "50")
    if len(raw_limit) > 3 or not raw_limit.isascii() or not raw_limit.isdecimal():
        raise OldapErrorValue("Inventory limit must be an integer.")
    secret = TokenSettings.from_environment().require_access_secret()
    key = hashlib.sha256(("oldap:archive-inventory-key:v1:" + secret).encode()).digest()
    return ArchiveInventory(
        authenticated_connection(), project, cursor_secret=key
    ).page(
        request.args.get("folderIri"),
        limit=int(raw_limit),
        cursor=request.args.get("cursor"),
    )


def _review_body():
    """Bound and read JSON for all three reviewed-adoption operations."""
    request.max_content_length = MAX_REQUEST_BYTES
    if not request.is_json or not isinstance(
        body := request.get_json(silent=True), dict
    ):
        raise OldapErrorValue("A JSON object is required.")
    return body


@archive_structure_bp.post("/archive/<project>/structure/proposal")
@require_auth
@domain_response
def structure_proposal(project):
    """Suggest eligible source copies/reuse without changing stored resources."""
    from oldaplib.src.archive_adoption import ArchiveAdoption

    body = _review_body()
    return ArchiveAdoption(authenticated_connection(), project).proposal(body)


@archive_structure_bp.post("/archive/<project>/structure/defaults/proposal")
@require_auth
@domain_response
def archive_default_proposal(project):
    """Read current folder defaults and permission-filtered provenance suggestions."""
    from oldaplib.src.archive_adoption import ArchiveAdoption

    return ArchiveAdoption(authenticated_connection(), project).default_proposal(
        _review_body()
    )


@archive_structure_bp.post("/archive/<project>/structure/preflight")
@require_auth
@domain_response
def structure_preflight(project):
    """Validate a caller-edited plan and return its stateless review digest."""
    from oldaplib.src.archive_adoption import ArchiveAdoption

    body = _review_body()
    return ArchiveAdoption(authenticated_connection(), project).preflight(body)


@archive_structure_bp.post("/archive/<project>/structure/apply")
@require_auth
@domain_response
def structure_apply(project):
    """Apply a confirmed unchanged plan, or disclose its authorized exact receipt."""
    from oldaplib.src.archive_adoption import ArchiveAdoption

    body = _review_body()
    return ArchiveAdoption(authenticated_connection(), project).apply(
        body, operation_id=request.headers.get("Idempotency-Key")
    )
