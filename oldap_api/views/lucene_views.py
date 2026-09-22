"""Authenticated administration of the single Lucene connector owned by a project.

The library enforces model administration and optimistic replacement checks.
Connector commands rebuild external indexes and are not RDF transactions.
"""

from flask import Blueprint, jsonify, request
from oldap_api.authentication import authenticated_connection, require_auth
from oldaplib.src.helpers.oldaperror import (
    OldapError, OldapErrorAlreadyExists, OldapErrorNoPermission,
    OldapErrorNotFound, OldapErrorValue,
)

lucene_bp = Blueprint("lucene", __name__, url_prefix="/admin/lucene")


@lucene_bp.route("/<project>", methods=["GET", "PUT"])
@require_auth
def project_connector(project):
    """Read native options or apply create/replace with a reviewed revision.

    GET returns configuration/revision null when the project has no connector.
    PUT requires mode, configuration and (for replace) expectedRevision, including
    explicit null to assert absence. A stale revision returns 409 before dropping.
    """
    try:
        # Additive feature: older library installations keep existing routes usable.
        from oldaplib.src.lucene_connector import ProjectLuceneConnector, configuration_revision
    except ImportError:
        return jsonify(message="Install the oldaplib Lucene connector update."), 503
    try:
        connector = ProjectLuceneConnector(authenticated_connection(), project)
        if request.method == "GET":
            configuration = connector.read()
            return jsonify(name=connector.name, configuration=configuration,
                           revision=configuration_revision(configuration))
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) - {"mode", "configuration", "expectedRevision"}:
            raise OldapErrorValue("Expected mode, configuration and optional expectedRevision.")
        if body.get("mode") not in {"create", "replace"} or "configuration" not in body:
            raise OldapErrorValue("Require mode create/replace and configuration.")
        if body["mode"] == "replace" and "expectedRevision" not in body:
            raise OldapErrorValue("Replacement requires expectedRevision (null for absence).")
        revision = body.get("expectedRevision")
        if revision is not None and (not isinstance(revision, str) or len(revision) != 64
                                     or any(c not in "0123456789abcdef" for c in revision)):
            raise OldapErrorValue("expectedRevision must be a SHA-256 revision or null.")
        status = connector.apply(body["configuration"], mode=body["mode"], expected_revision=revision)
        return jsonify(name=connector.name, status=status), 200
    except OldapErrorNoPermission as error:
        return jsonify(message=str(error)), 403
    except OldapErrorNotFound as error:
        return jsonify(message=str(error)), 404
    except OldapErrorAlreadyExists as error:
        return jsonify(message=str(error)), 409
    except (OldapErrorValue, ValueError, TypeError) as error:
        return jsonify(message=str(error)), 400
    except OldapError as error:
        return jsonify(message=str(error)), 500
