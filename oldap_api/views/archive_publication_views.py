"""Authenticated project-neutral publication review and atomic apply endpoints."""

from flask import Blueprint, request
from oldap_api.authentication import authenticated_connection, require_auth
from oldap_api.views.archive_structure_views import domain_response
from oldaplib.src.helpers.oldaperror import OldapErrorValue

archive_publication_bp = Blueprint("archive_publication", __name__)


def publication_service(project):
    """Resolve the versioned library service only when the new route is used.

    This lets an operator stage the API source before upgrading its library;
    the new feature fails closed until the matching library is installed.
    """
    from oldaplib.src.archive_publication import ArchivePublication

    return ArchivePublication(authenticated_connection(), project)


@archive_publication_bp.after_request
def private_response(response):
    """Prevent intermediary caching of authorization and reviewed resources."""
    response.headers["Cache-Control"] = "no-store"
    return response


def body():
    """Read a bounded object; the domain service checks its closed schema."""
    request.max_content_length = 8192
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise OldapErrorValue("A JSON object is required.")
    return value


@archive_publication_bp.get("/archive/<project>/publication/capabilities")
@require_auth
@domain_response
def capabilities(project):
    """Expose configured publication capability for this authenticated actor."""
    return publication_service(project).capabilities(request.args.get("resourceIri"))


@archive_publication_bp.post("/archive/<project>/publication/preview")
@require_auth
@domain_response
def preview(project):
    """Review the complete affected set without changing stored resources."""
    return publication_service(project).preview(body())


@archive_publication_bp.post("/archive/<project>/publication/apply")
@require_auth
@domain_response
def apply(project):
    """Commit a reviewed command with an actor-scoped idempotency key."""
    return publication_service(project).apply(
        body(), request.headers.get("Idempotency-Key")
    )


@archive_publication_bp.get("/archive/<project>/publication/operations/<operation_id>")
@require_auth
@domain_response
def operation(project, operation_id):
    """Resolve an uncertain response without repeating publication."""
    return publication_service(project).operation(operation_id)
