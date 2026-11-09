"""Additive project-scoped managed Jena fulltext administration."""
from flask import Blueprint, jsonify, request
from oldap_api.authentication import authenticated_connection, require_auth
from oldaplib.src.helpers.oldaperror import (
    OldapError, OldapErrorAlreadyExists, OldapErrorConfiguration,
    OldapErrorNoPermission, OldapErrorNotFound, OldapErrorValue,
)

fulltext_bp = Blueprint('fulltext', __name__, url_prefix='/admin/fulltext')


@fulltext_bp.after_request
def no_store(response):
    """Prevent administration state and errors from being cached."""
    response.headers['Cache-Control'] = 'no-store'
    return response


@fulltext_bp.route('/<project>', methods=['GET', 'PUT'])
@require_auth
def project_fulltext(project):
    """GET state; PUT graph/fields plus mandatory expectedRevision (null if absent)."""
    try:
        from oldaplib.src.project_fulltext import ProjectFulltext
        service = ProjectFulltext(authenticated_connection(), project)
        if request.method == 'GET':
            return jsonify(service.read())
        if request.content_length is not None and request.content_length > 262144:
            return jsonify(message='Fulltext request too large.'), 413
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {'configuration', 'expectedRevision'}:
            raise OldapErrorValue('Require configuration and expectedRevision (null for absence).')
        return jsonify(service.apply(body['configuration'], body['expectedRevision']))
    except (ImportError, OldapErrorConfiguration):
        return jsonify(message='Managed fulltext unavailable or outcome uncertain; inspect state before retrying.'), 503
    except OldapErrorNoPermission as error:
        return jsonify(message=str(error)), 403
    except OldapErrorNotFound as error:
        return jsonify(message=str(error)), 404
    except OldapErrorAlreadyExists as error:
        return jsonify(message=str(error)), 409
    except (OldapErrorValue, ValueError, TypeError) as error:
        return jsonify(message=str(error)), 400
    except OldapError:
        return jsonify(message='Fulltext administration failed.'), 500
