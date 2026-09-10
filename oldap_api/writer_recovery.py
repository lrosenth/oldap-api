"""Authorized recovery application service for the additive WR-03 HTTP adapters.

The service uses current RDF role membership on every call, including retries and
status reads. It deliberately has no archive-policy/admin-permission shortcut.
Runtime control and operational evidence creation are unavailable in this module.
"""

import os
from urllib.parse import urlsplit

from redis import Redis
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import (
    OldapErrorConfiguration,
    OldapErrorNoPermission,
)
from oldaplib.src.writer_recovery import WriterRecovery
from oldaplib.src.xsd.iri import Iri


def require_recovery_role(connection, role_iri: str) -> str:
    """Authorize an active user from authoritative RDF, never cached JWT roles.

    Args:
        connection: Request-authenticated OLDAP connection.
        role_iri: Explicit absolute operational role IRI from server configuration.

    Returns:
        The authenticated actor IRI for the durable recovery audit.

    Raises:
        OldapErrorNoPermission: If the current active user lacks this exact role.
        OldapErrorConfiguration: If the dedicated role is not configured safely.
    """
    if (
        not role_iri
        or urlsplit(role_iri).scheme not in ("http", "https", "urn")
        or any(c in role_iri for c in '<>"{}\\\r\n ')
    ):
        raise OldapErrorConfiguration(
            "An absolute writer-recovery role IRI is required."
        )
    role = Iri(role_iri, validate=True)
    context = Context(name=connection.context_name)
    query = context.sparql_context + f"""ASK {{ GRAPH oldap:admin {{
        {connection.userIri.toRdf} oldap:isActive true ; oldap:hasRole {role.toRdf} .
        {role.toRdf} a oldap:Role .
    }} }}"""
    if connection.query(query, timeout=(5, 10)).get("boolean") is not True:
        raise OldapErrorNoPermission(
            "Writer recovery requires the configured operational role."
        )
    return str(connection.userIri)


class WriterRecoveryService:
    """Backend boundary for authenticated recovery adapters; deny by default."""

    def __init__(self, connection, *, recovery: WriterRecovery | None = None):
        self.connection = connection
        self.role = os.getenv("OLDAP_WRITER_RECOVERY_ROLE_IRI", "")
        if recovery is None:
            url = os.getenv("OLDAP_WRITER_RECOVERY_REDIS_URL", "")
            domain = os.getenv("OLDAP_WRITER_DOMAIN", "")
            if not url or not domain or not self.role:
                raise OldapErrorConfiguration("Writer recovery is not configured.")
            recovery = WriterRecovery(
                Redis.from_url(
                    url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=10,
                ),
                domain,
                inventory_digest=os.getenv(
                    "OLDAP_WRITER_RECOVERY_INVENTORY_SHA256", ""
                ),
            )
        self.recovery = recovery

    def status(self) -> dict:
        """Return restricted diagnostics after a fresh operational-role check."""
        require_recovery_role(self.connection, self.role)
        return self.recovery.status()

    def operation(self, operation_id: str) -> dict:
        """Read the durable result; role revocation also revokes audit access."""
        require_recovery_role(self.connection, self.role)
        return self.recovery.operation(operation_id)

    def begin(self, *, operation_id: str, expected_revision: str, reason: str) -> dict:
        """Authorize and freeze the reviewed writer; never trust an actor from input."""
        actor = require_recovery_role(self.connection, self.role)
        return self.recovery.begin(
            operation_id=operation_id,
            expected_revision=expected_revision,
            actor=actor,
            reason=reason,
        )

    def finish(self, *, operation_id: str) -> dict:
        """Reauthorize immediately before attempting an evidence-backed release."""
        actor = require_recovery_role(self.connection, self.role)
        return self.recovery.finish(operation_id=operation_id, actor=actor)


def recovery_capabilities(connection) -> dict:
    """Discover access without disclosing owner/runtime facts or connecting to Redis."""
    names = (
        "OLDAP_WRITER_DOMAIN",
        "OLDAP_WRITER_RECOVERY_REDIS_URL",
        "OLDAP_WRITER_RECOVERY_ROLE_IRI",
        "OLDAP_WRITER_RECOVERY_INVENTORY_SHA256",
    )
    if not all(os.getenv(name, "").strip() for name in names):
        return {"enabled": False, "canRecover": False}
    try:
        require_recovery_role(connection, os.environ["OLDAP_WRITER_RECOVERY_ROLE_IRI"])
    except OldapErrorNoPermission:
        return {"enabled": True, "canRecover": False}
    return {"enabled": True, "canRecover": True}


def operation_summary(service: WriterRecoveryService, result: dict) -> dict:
    """Project an already authorized record onto the closed browser contract."""
    state = service.recovery.readiness(result)
    summary = {
        "operationId": result["operationId"],
        "state": state,
        "requestedAt": result["requestedAt"],
        "reason": result["request"]["reason"],
        "canFinish": state == "ready",
    }
    if result.get("completedAt"):
        summary["completedAt"] = result["completedAt"]
    return summary
