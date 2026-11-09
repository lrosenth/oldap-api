"""Private token verification for the Jena service; no database recursion."""

import os
import secrets
from flask import Blueprint, jsonify, request
from oldap_api.backend import backend_name
from oldaplib.src.authentication import TokenCodec
from oldaplib.src.helpers.oldaperror import OldapError

jena_identity_bp = Blueprint("jena_identity", __name__)


@jena_identity_bp.route("/internal/jena/identity", methods=["POST"])
def verify_identity():
    """Verify a token with existing codecs after a separate service credential.

    This route must remain private at the deployment proxy. It never builds a
    database connection, avoiding a verification/connection dependency cycle.
    """
    if backend_name() != "jena":
        return jsonify(message="Unavailable."), 404
    expected = os.getenv("OLDAP_JENA_IDENTITY_KEY")
    supplied = request.headers.get("Authorization", "")
    # HTTP header values may contain non-ASCII bytes; compare encoded values
    # so malformed credentials are rejected instead of raising TypeError.
    if not expected or not secrets.compare_digest(
        supplied.encode("utf-8"), ("Bearer " + expected).encode("utf-8")
    ):
        return jsonify(message="Authentication required."), 401
    if not request.content_length or request.content_length > 16384:
        return jsonify(message="Invalid verification request."), 413
    tokens = request.form.getlist("token")
    result = {"active": False}
    if len(tokens) == 1:
        try:
            context = TokenCodec.from_environment().decode_access_token(tokens[0])
            result = {"active": True, "sub": str(context.userIri)}
        except OldapError:
            pass
    response = jsonify(result)
    response.headers["Cache-Control"] = "no-store"
    return response
