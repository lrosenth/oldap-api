"""Trusted frontend destinations for reset and asynchronous job mail.

Only server-owned configuration supplies URLs. Browser Origin selects a frontend;
this is routing metadata, never authentication or project authorization. Jobs keep
only the stable ID so background workers do not depend on an HTTP request.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from string import Formatter
from urllib.parse import quote, urlsplit


class FrontendRequestError(ValueError):
    """An explicitly supplied browser origin has no configured destination."""


def registry() -> dict:
    """Load and validate the optional server-owned JSON registry, failing closed."""
    filename = os.getenv("OLDAP_FRONTENDS_FILE")
    if not filename:
        return {}
    try:
        entries = json.loads(Path(filename).read_text())
        if not isinstance(entries, dict) or not entries:
            raise ValueError("Expected a nonempty frontend mapping")
        origins = set()
        fields = {
            "password_reset": set(),
            "import_status": {"import_id"},
            "export_status": {"export_id"},
        }
        for key, entry in entries.items():
            if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", key):
                raise ValueError("Invalid frontend ID")
            if set(entry) - {"origin", "origins", "display_name", "routes"} or not {
                "origin",
                "display_name",
                "routes",
            } <= set(entry):
                raise ValueError("Invalid frontend fields")
            origin = entry["origin"]
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"https", "http"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "\\" in origin
                or any(c.isspace() for c in origin)
            ):
                raise ValueError("Expected an exact HTTP(S) origin")
            if parsed.scheme == "http" and parsed.hostname not in {
                "localhost",
                "127.0.0.1",
                "::1",
            }:
                raise ValueError("Public frontend origins require HTTPS")
            aliases = entry.get("origins", [origin])
            if (
                not isinstance(aliases, list)
                or not aliases
                or any(not isinstance(v, str) for v in aliases)
            ):
                raise ValueError("Expected exact browser origins")
            for alias in aliases:
                parsed_alias = urlsplit(alias)
                if (
                    parsed_alias.scheme not in {"http", "https"}
                    or not parsed_alias.netloc
                    or parsed_alias.path
                    or parsed_alias.query
                    or parsed_alias.fragment
                    or parsed_alias.username
                    or parsed_alias.password
                    or "\\" in alias
                    or any(c.isspace() for c in alias)
                ):
                    raise ValueError("Invalid browser origin")
                if alias in origins:
                    raise ValueError("Ambiguous frontend origin")
                origins.add(alias)
            if (
                not isinstance(entry["display_name"], str)
                or not entry["display_name"].strip()
            ):
                raise ValueError("Missing display name")
            routes = entry["routes"]
            if set(routes) != set(fields):
                raise ValueError("All three mail routes are required")
            for purpose, route in routes.items():
                if (
                    not isinstance(route, str)
                    or not route.startswith("/")
                    or route.startswith("//")
                    or any(c in route for c in "\\?#%")
                    or any(c.isspace() for c in route)
                    or any(segment in {".", ".."} for segment in route.split("/"))
                ):
                    raise ValueError("Expected a local absolute route")
                parts = list(Formatter().parse(route))
                if {field for _, field, _, _ in parts if field is not None} != fields[
                    purpose
                ] or any(spec or conversion for _, _, spec, conversion in parts):
                    raise ValueError("Invalid route placeholders")
        return entries
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        raise RuntimeError("Invalid OLDAP frontend registry") from error


def frontend_for_origin(origin: str | None) -> str | None:
    """Resolve browser routing before side effects; absent Origin uses legacy mail."""
    entries = registry()
    if not entries or origin is None:
        return None
    for key, entry in entries.items():
        if origin in entry.get("origins", [entry["origin"]]):
            return key
    raise FrontendRequestError("No email frontend is configured for this origin.")


def mail_link(frontend_id: str | None, purpose: str, **values: str) -> str:
    """Build a trusted URL; removed IDs fail instead of silently changing destination."""
    if frontend_id is not None:
        entry = registry().get(frontend_id)
        if entry is None:
            raise RuntimeError("The job email frontend is no longer configured")
        path = entry["routes"][purpose].format(
            **{
                key: quote(str(value), safe="").replace(".", "%2E")
                for key, value in values.items()
            }
        )
        return entry["origin"] + path
    base = os.getenv("OLDAP_PUBLIC_APP_URL")
    if purpose == "password_reset":
        base = os.getenv("OLDAP_PASSWORD_RESET_FRONTEND_URL") or base
    if not base:
        raise RuntimeError("Legacy email frontend URL is not configured")
    paths = {
        "password_reset": "/password-reset",
        "import_status": "/imports/{import_id}",
        "export_status": "/exports/{export_id}",
    }
    return base.rstrip("/") + paths[purpose].format(
        **{key: quote(str(value), safe="") for key, value in values.items()}
    )


def mail_display_name(frontend_id: str | None) -> str:
    """Return trusted presentation text; it never grants access to a project."""
    if frontend_id is None:
        return "OLDAP"
    entry = registry().get(frontend_id)
    if entry is None:
        raise RuntimeError("The email frontend is no longer configured")
    return entry["display_name"]
