"""Authentication boundary for internal ZIP export worker operations."""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import jwt
from flask import Response, current_app, g, jsonify, request

EXPORT_SERVICE_TOKEN_TYPE = "export-service"
EXPORT_SERVICE_AUDIENCE = "oldap-api-export-service"
_PRINCIPAL_KEY = "oldap_export_service_principal"

P = ParamSpec("P")
R = TypeVar("R")


def require_export_service(view: Callable[P, R]) -> Callable[P, R | Response]:
    """Accept only the dedicated audience-bound export service JWT."""

    @wraps(view)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R | Response:
        token = _bearer_token()
        if token is None:
            return _failure(401)
        try:
            claims = _decode(token)
        except RuntimeError as error:
            current_app.logger.error(
                "Export service authentication unavailable: %s", error
            )
            return _failure(503)
        except jwt.PyJWTError:
            return _failure(401)
        setattr(g, _PRINCIPAL_KEY, claims["sub"])
        return view(*args, **kwargs)

    setattr(wrapped, "_oldap_requires_export_service", True)
    return wrapped


def export_service_principal() -> str:
    """Return the authenticated internal service subject."""

    principal = getattr(g, _PRINCIPAL_KEY, None)
    if principal is None:
        raise RuntimeError("Export service principal requested outside its boundary.")
    return str(principal)


def _decode(token: str) -> dict[str, Any]:
    secret = os.getenv("OLDAP_EXPORT_SERVICE_JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError(
            "OLDAP_EXPORT_SERVICE_JWT_SECRET must contain at least 32 bytes."
        )
    other_names = (
        "OLDAP_ACCESS_JWT_SECRET",
        "OLDAP_REFRESH_JWT_SECRET",
        "OLDAP_MEDIA_JWT_SECRET",
        "OLDAP_PASSWORD_RESET_JWT_SECRET",
        "OLDAP_IMPORT_UPLOAD_JWT_SECRET",
        "OLDAP_IMPORT_SERVICE_JWT_SECRET",
        "OLDAP_IMPORT_RECORDS_JWT_SECRET",
        "OLDAP_EXPORT_DOWNLOAD_JWT_SECRET",
    )
    if secret in {value for name in other_names if (value := os.getenv(name, ""))}:
        raise RuntimeError("The export service JWT secret must be purpose-specific.")
    claims = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience=EXPORT_SERVICE_AUDIENCE,
        issuer=os.getenv("OLDAP_JWT_ISSUER", "https://oldap.org"),
        options={"require": ["typ", "sub", "iat", "exp", "iss", "aud"]},
    )
    if claims.get("typ") != EXPORT_SERVICE_TOKEN_TYPE or not claims.get("sub"):
        raise jwt.InvalidTokenError("Wrong export service token purpose.")
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
    response = jsonify({"message": "Export service authentication required."})
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    if status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return response
