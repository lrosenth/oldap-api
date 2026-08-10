"""Authenticated HTTP endpoints for archive YAML export and import workflows."""

from __future__ import annotations

import re

from flask import Blueprint, Response, current_app, jsonify, request
from oldaplib.src.archive_import import ArchiveImportError
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorNotFound

from oldap_api.archive_workflow import (
    build_visible_staging_archive_proposal,
    apply_archive_upload,
    archive_plan_json,
    prepare_archive_upload,
    render_archive_proposal,
)
from oldap_api.authentication import authenticated_connection, require_auth


archive_workflow_bp = Blueprint("archive_workflow", __name__, url_prefix="/archive")
MAX_ARCHIVE_YAML_BYTES = 2_000_000


def _download_filename(project: str) -> str:
    """Return a conservative ASCII attachment filename."""

    safe_project = re.sub(r"[^A-Za-z0-9_-]+", "-", project).strip("-") or "project"
    return f"archive-structure-proposal-{safe_project}.yaml"


@archive_workflow_bp.get("/<project>/staging-proposal")
@require_auth
def download_staging_archive_proposal(project: str):
    """Download visible Staging folders as an editable archive YAML proposal."""

    staging_area_iri = request.args.get("stagingAreaIri", "").strip()
    if not staging_area_iri:
        return jsonify({"message": "stagingAreaIri is required."}), 400
    try:
        proposal = build_visible_staging_archive_proposal(
            authenticated_connection(),
            project,
            staging_area_iri,
        )
    except OldapErrorNoPermission:
        return jsonify({"message": "The selected StagingArea was not found."}), 404
    except OldapErrorNotFound:
        return jsonify({"message": "The selected StagingArea was not found."}), 404
    except (ValueError, OldapError) as error:
        current_app.logger.info("Staging archive proposal rejected: %s", error)
        return jsonify({"message": str(error)}), 400

    response = Response(render_archive_proposal(proposal), content_type="application/yaml; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{_download_filename(project)}"'
    response.headers["X-Archive-Proposal-Warnings"] = str(len(proposal.warnings))
    response.headers["Cache-Control"] = "no-store"
    return response


def _uploaded_yaml() -> tuple[str | None, tuple[Response, int] | None]:
    """Read bounded YAML text from JSON or multipart input; never accept paths."""

    if request.is_json:
        payload = request.get_json(silent=True)
        value = payload.get("yaml") if isinstance(payload, dict) else None
        if not isinstance(value, str):
            return None, (jsonify({"message": "A YAML string is required."}), 400)
        raw = value.encode("utf-8")
    elif "file" in request.files:
        raw = request.files["file"].stream.read(MAX_ARCHIVE_YAML_BYTES + 1)
    else:
        return None, (jsonify({"message": "JSON yaml or a multipart file is required."}), 415)
    if len(raw) > MAX_ARCHIVE_YAML_BYTES:
        return None, (jsonify({"message": "Archive YAML exceeds the 2 MB limit."}), 413)
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, (jsonify({"message": "Archive YAML must be UTF-8."}), 400)


def _workflow_error(error: Exception):
    """Map expected archive failures to stable non-leaking HTTP responses."""

    if isinstance(error, OldapErrorNoPermission):
        return jsonify({"message": str(error)}), 403
    if isinstance(error, OldapErrorNotFound):
        return jsonify({"message": "A required resource was not found."}), 404
    if isinstance(error, ArchiveImportError):
        return jsonify({
            "message": str(error),
            "createdIris": [str(iri) for iri in error.created_iris],
            "rollbackFailures": list(error.rollback_failures),
        }), 500
    message = str(error)
    status = 409 if "already exists" in message or "does not match" in message else 400
    return jsonify({"message": message}), status


@archive_workflow_bp.post("/<project>/imports/preflight")
@require_auth
def preflight_archive_import(project: str):
    """Validate and resolve exact YAML without writing any OLDAP resource."""

    yaml_text, input_error = _uploaded_yaml()
    if input_error:
        return input_error
    try:
        prepared = prepare_archive_upload(authenticated_connection(), project, yaml_text)
    except (ValueError, OldapError) as error:
        return _workflow_error(error)
    response = jsonify(archive_plan_json(prepared))
    response.headers["Cache-Control"] = "no-store"
    return response


@archive_workflow_bp.post("/<project>/imports/apply")
@require_auth
def apply_archive_import_endpoint(project: str):
    """Explicitly confirm and apply the exact YAML bound during preflight."""

    if not request.is_json:
        return jsonify({"message": "Apply requires a JSON request."}), 415
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("confirm") is not True:
        return jsonify({"message": "Explicit confirmation is required."}), 400
    expected_hash = payload.get("documentHash")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        return jsonify({"message": "A valid preflight documentHash is required."}), 400
    yaml_text, input_error = _uploaded_yaml()
    if input_error:
        return input_error
    try:
        prepared, created = apply_archive_upload(
            authenticated_connection(), project, yaml_text, expected_hash
        )
    except (ValueError, OldapError) as error:
        connection = authenticated_connection()
        current_app.logger.warning(
            "archive_yaml_apply user=%s project=%s hash=%s result=failure error=%s",
            getattr(connection, "userIri", getattr(connection, "userid", "unknown")),
            project,
            expected_hash,
            error.__class__.__name__,
        )
        return _workflow_error(error)
    connection = authenticated_connection()
    current_app.logger.info(
        "archive_yaml_apply user=%s project=%s hash=%s created=%d result=success",
        getattr(connection, "userIri", getattr(connection, "userid", "unknown")),
        project,
        prepared.document_hash,
        len(created),
    )
    response = jsonify({
        "documentHash": prepared.document_hash,
        "createdCount": len(created),
        "createdIris": [str(iri) for iri in created],
    })
    response.status_code = 201
    response.headers["Cache-Control"] = "no-store"
    return response
