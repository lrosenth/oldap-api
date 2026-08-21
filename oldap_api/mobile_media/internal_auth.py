"""Purpose-specific authentication for the internal mobile-media commit."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar
from uuid import uuid4

import jwt
from flask import Response, current_app, jsonify, request

MOBILE_MEDIA_TOKEN_TYPE = "mobile-media-service"
MOBILE_MEDIA_TOKEN_PURPOSE = "mobile-media-commit"
MOBILE_MEDIA_AUDIENCE = "oldap-api-mobile-media"
MOBILE_MEDIA_SUBJECT = "oldap-mediaserver"
MAX_TOKEN_LIFETIME_SECONDS = 300
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

P = ParamSpec("P")
R = TypeVar("R")


def require_mobile_media_service(view: Callable[P, R]) -> Callable[P, R | Response]:
    """Accept only the dedicated, short-lived media-to-OLDAP service JWT."""

    @wraps(view)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R | Response:
        token = _bearer_token()
        if token is None:
            return _failure(401, "invalid_credentials", False)
        try:
            _decode(token)
        except RuntimeError as error:
            current_app.logger.error(
                "Mobile-media service authentication unavailable: %s", error
            )
            return _failure(503, "authentication_unavailable", True)
        except jwt.PyJWTError:
            return _failure(401, "invalid_credentials", False)
        return view(*args, **kwargs)

    setattr(wrapped, "_oldap_requires_mobile_media_service", True)
    return wrapped


def _decode(token: str) -> dict[str, Any]:
    secret = os.getenv("OLDAP_MOBILE_MEDIA_SERVICE_JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError(
            "OLDAP_MOBILE_MEDIA_SERVICE_JWT_SECRET must contain at least 32 bytes."
        )
    other_names = (
        "OLDAP_ACCESS_JWT_SECRET",
        "OLDAP_REFRESH_JWT_SECRET",
        "OLDAP_MEDIA_JWT_SECRET",
        "OLDAP_PASSWORD_RESET_JWT_SECRET",
        "OLDAP_IMPORT_UPLOAD_JWT_SECRET",
        "OLDAP_IMPORT_SERVICE_JWT_SECRET",
        "OLDAP_IMPORT_RECORDS_JWT_SECRET",
        "OLDAP_EXPORT_SERVICE_JWT_SECRET",
        "OLDAP_EXPORT_DOWNLOAD_JWT_SECRET",
    )
    if secret in {value for name in other_names if (value := os.getenv(name, ""))}:
        raise RuntimeError(
            "The mobile-media service JWT secret must be purpose-specific."
        )
    claims = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience=MOBILE_MEDIA_AUDIENCE,
        issuer=os.getenv("OLDAP_JWT_ISSUER", "https://oldap.org"),
        options={"require": ["typ", "purpose", "sub", "iat", "exp", "iss", "aud"]},
    )
    if (
        claims.get("typ") != MOBILE_MEDIA_TOKEN_TYPE
        or claims.get("purpose") != MOBILE_MEDIA_TOKEN_PURPOSE
        or claims.get("sub") != MOBILE_MEDIA_SUBJECT
    ):
        raise jwt.InvalidTokenError("Wrong mobile-media service token purpose.")
    issued_at = claims.get("iat")
    expires_at = claims.get("exp")
    if (
        isinstance(issued_at, bool)
        or isinstance(expires_at, bool)
        or not isinstance(issued_at, (int, float))
        or not isinstance(expires_at, (int, float))
        or expires_at <= issued_at
        or expires_at - issued_at > MAX_TOKEN_LIFETIME_SECONDS
    ):
        raise jwt.InvalidTokenError("Mobile-media service token lifetime is invalid.")
    return claims


def _bearer_token() -> str | None:
    value = request.headers.get("Authorization")
    if not value:
        return None
    parts = value.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        return None
    return parts[1]


def _failure(status: int, code: str, retryable: bool) -> Response:
    supplied = request.headers.get("X-Request-ID", "")
    trace_id = supplied if REQUEST_ID_RE.fullmatch(supplied) else str(uuid4())
    response = jsonify(
        {
            "type": f"https://api.fasnacht.digital/problems/{code.replace('_', '-')}",
            "title": "Mobile-media service authentication failed",
            "status": status,
            "code": code,
            "traceId": trace_id,
            "retryable": retryable,
        }
    )
    response.status_code = status
    response.content_type = "application/problem+json"
    response.headers["Cache-Control"] = "no-store"
    if status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return response
