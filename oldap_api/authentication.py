"""Shared bearer-authentication boundary for protected OLDAP API views."""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from flask import Response, current_app, g, jsonify, request
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import (
    OldapError,
    OldapErrorConfiguration,
)

P = ParamSpec("P")
R = TypeVar("R")
_CONNECTION_KEY = "oldap_authenticated_connection"


def _authentication_failure(status: int = 401) -> Response:
    """Return the uniform response used for all bearer-authentication failures."""
    response = jsonify({"message": "Authentication required."})
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    if status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return response


def _bearer_token() -> str | None:
    """Return a strictly parsed bearer token without validating it."""
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        return None
    return parts[1]


def require_auth(view: Callable[P, R]) -> Callable[P, R | Response]:
    """Validate an access token once and expose its connection to the view.

    Missing, malformed, expired, wrong-purpose, and otherwise invalid bearer
    credentials deliberately receive the same ``401`` response. Runtime token
    configuration failures remain distinguishable as ``503`` operational
    errors.
    """

    @wraps(view)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R | Response:
        token = _bearer_token()
        if token is None:
            return _authentication_failure()
        try:
            connection = Connection(token=token, context_name="DEFAULT")
        except OldapErrorConfiguration as error:
            current_app.logger.error(
                "Bearer authentication is not configured: %s", error
            )
            return _authentication_failure(status=503)
        except OldapError:
            return _authentication_failure()
        setattr(g, _CONNECTION_KEY, connection)
        return view(*args, **kwargs)

    setattr(wrapped, "_oldap_requires_auth", True)
    return wrapped


def authenticated_connection() -> Connection:
    """Return the connection established by :func:`require_auth`.

    Raises:
        RuntimeError: If a protected view was not decorated with
            :func:`require_auth`.
    """
    connection = getattr(g, _CONNECTION_KEY, None)
    if connection is None:
        raise RuntimeError("Authenticated connection requested outside require_auth")
    return cast(Connection, connection)
