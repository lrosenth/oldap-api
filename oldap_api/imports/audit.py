"""Privacy-preserving operational audit events for ZIP import mutations."""

from __future__ import annotations

from typing import Protocol
import traceback

from .domain import ImportJob


class AuditLogger(Protocol):
    """Minimal logger contract required by the import audit boundary."""

    def info(self, message: str, *args: object) -> None: ...

    def error(self, message: str, *args: object) -> None: ...


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


def log_import_failure(logger: AuditLogger, error: Exception, *, endpoint: str,
                       request_id: str) -> None:
    """Record exception types and code locations without exception contents.

    Follow the bounded explicit/implicit cause chain, respecting suppressed
    context. Never format exception messages, source lines, locals, request
    bodies or headers: database and HTTP errors may contain private payloads.
    The request ID correlates the public error with this server-only diagnostic.
    """
    chain = []
    seen = set()
    current = error
    while current is not None and id(current) not in seen and len(chain) < 8:
        seen.add(id(current))
        frames = traceback.extract_tb(current.__traceback__)
        locations = [f"{frame.filename.rsplit('/', 1)[-1]}:{frame.name}:{frame.lineno}"
                     for frame in frames[-12:]]
        chain.append({"type": type(current).__name__, "locations": locations})
        current = (current.__cause__ if current.__cause__ is not None else
                   None if current.__suppress_context__ else current.__context__)
    logger.error("import_failure endpoint=%s requestId=%s exceptions=%s",
                 endpoint, request_id, chain)
