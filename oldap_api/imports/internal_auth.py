"""Authentication boundary for non-public ZIP import service operations."""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import jwt
from flask import Response, current_app, g, jsonify, request

IMPORT_SERVICE_TOKEN_TYPE = "import-service"
IMPORT_SERVICE_AUDIENCE = "oldap-api-import-service"
_PRINCIPAL_KEY = "oldap_import_service_principal"

P = ParamSpec("P")
R = TypeVar("R")


def require_import_service(view: Callable[P, R]) -> Callable[P, R | Response]:
    """Accept only a dedicated, audience-bound internal service JWT."""

    @wraps(view)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R | Response:
        token = _bearer_token()
        if token is None:
            return _failure(401)
        try:
            claims = _decode(token)
        except RuntimeError as error:
            current_app.logger.error(
                "Import service authentication unavailable: %s", error
            )
            return _failure(503)
        except jwt.PyJWTError:
            return _failure(401)
        setattr(g, _PRINCIPAL_KEY, claims["sub"])
        return view(*args, **kwargs)

    setattr(wrapped, "_oldap_requires_import_service", True)
    return wrapped


def import_service_principal() -> str:
    """Return the authenticated internal service subject."""
    principal = getattr(g, _PRINCIPAL_KEY, None)
    if principal is None:
        raise RuntimeError("Import service principal requested outside its boundary.")
    return str(principal)


def _decode(token: str) -> dict[str, Any]:
    secret = os.getenv("OLDAP_IMPORT_SERVICE_JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError(
            "OLDAP_IMPORT_SERVICE_JWT_SECRET must contain at least 32 bytes."
        )
    other = {
        os.getenv("OLDAP_ACCESS_JWT_SECRET"),
        os.getenv("OLDAP_REFRESH_JWT_SECRET"),
        os.getenv("OLDAP_MEDIA_JWT_SECRET"),
        os.getenv("OLDAP_PASSWORD_RESET_JWT_SECRET"),
        os.getenv("OLDAP_IMPORT_UPLOAD_JWT_SECRET"),
    }
    if secret in {value for value in other if value}:
        raise RuntimeError("The import service JWT secret must be purpose-specific.")
    claims = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience=IMPORT_SERVICE_AUDIENCE,
        issuer=os.getenv("OLDAP_JWT_ISSUER", "https://oldap.org"),
        options={"require": ["typ", "sub", "iat", "exp", "iss", "aud"]},
    )
    if claims.get("typ") != IMPORT_SERVICE_TOKEN_TYPE or not claims.get("sub"):
        raise jwt.InvalidTokenError("Wrong import service token purpose.")
    return claims


def _bearer_token() -> str | None:
    value = request.headers.get("Authorization")
    if not value:
        return None
    parts = value.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        return None
    return parts[1]


def _failure(status: int) -> Response:
    response = jsonify({"message": "Import service authentication required."})
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    if status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return response
