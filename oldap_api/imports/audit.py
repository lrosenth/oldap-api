"""Privacy-preserving operational audit events for ZIP import mutations."""

from __future__ import annotations

from typing import Protocol

from .domain import ImportJob


class AuditLogger(Protocol):
    """Minimal logger contract required by the import audit boundary."""

    def info(self, message: str, *args: object) -> None: ...


def log_import_event(
    logger: AuditLogger,
    event: str,
    job: ImportJob,
    *,
    request_id: str,
) -> None:
    """Log only whitelisted identifiers and lifecycle facts.

    Original filenames, user/access/service/capability tokens, claim IDs,
    checksums, report contents, and validation details are deliberately absent.

    Args:
        logger: Application logger receiving the structured message.
        event: Internal constant naming the accepted mutation.
        job: Persisted job after the mutation.
        request_id: Sanitized correlation identifier for the HTTP request.
    """
    logger.info(
        "import_audit event=%s importId=%s state=%s stateVersion=%d requestId=%s",
        event,
        job.import_id,
        job.state.value,
        job.state_version,
        request_id,
    )
