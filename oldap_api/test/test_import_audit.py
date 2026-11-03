"""Privacy boundary tests for ZIP import operational audit logging."""

from datetime import UTC, datetime

from oldap_api.imports.audit import log_import_event
from oldap_api.imports.domain import ImportJob, ImportState, TargetSnapshot


class RecordingLogger:
    """Capture the formatted logger call without relying on global logging."""

    def __init__(self) -> None:
        self.message = ""

    def info(self, message: str, *args: object) -> None:
        self.message = message % args


def test_audit_event_whitelists_fields_and_redacts_sensitive_values():
    current = datetime.now(UTC)
    job = ImportJob(
        import_id="11111111-1111-4111-8111-111111111111",
        state=ImportState.VALIDATING,
        state_version=1,
        created_at=current,
        updated_at=current,
        requested_by_iri="https://example.org/users/alice",
        requested_by_user_id="alice",
        target=TargetSnapshot(
            project_short_name="fasnacht",
            staging_area_iri="https://example.org/staging/area",
            staging_area_name="Secret area name",
            target_root_folder_iri="https://example.org/staging/root",
            target_root_folder_name="Secret folder name",
        ),
        original_file_name="Confidential collection.zip",
        declared_compressed_size_bytes=1_000,
        quota_reserved_bytes=50_000,
        sip_sha256="a" * 64,
        active_claim_id="22222222-2222-4222-8222-222222222222",
    )
    logger = RecordingLogger()

    log_import_event(logger, "sip_stored", job, request_id="request-42")

    assert "event=sip_stored" in logger.message
    assert f"importId={job.import_id}" in logger.message
    assert "requestId=request-42" in logger.message
    for secret in (
        job.original_file_name,
        job.requested_by_iri,
        job.target.staging_area_name,
        job.sip_sha256,
        job.active_claim_id,
    ):
        assert secret not in logger.message


def test_failure_records_chain_locations_without_messages_or_source(caplog):
    import logging
    from oldap_api.imports.audit import log_import_failure

    try:
        try:
            raise ValueError('private-query-and-token')
        except ValueError as cause:
            raise RuntimeError('private-response-body') from cause
    except RuntimeError as error:
        log_import_failure(logging.getLogger(__name__), error,
                           endpoint='internal_import.record_import_validation_result',
                           request_id='request-42')
    assert 'RuntimeError' in caplog.text
    assert 'ValueError' in caplog.text
    assert 'test_failure_records_chain_locations_without_messages_or_source' in caplog.text
    assert 'request-42' in caplog.text
    assert 'private-query-and-token' not in caplog.text
    assert 'private-response-body' not in caplog.text
    assert 'raise RuntimeError' not in caplog.text


def test_failure_respects_suppressed_context_and_cycles(caplog):
    import logging
    from oldap_api.imports.audit import log_import_failure

    try:
        try:
            raise ValueError('secret')
        except ValueError:
            raise RuntimeError('hidden') from None
    except RuntimeError as error:
        log_import_failure(logging.getLogger(__name__), error,
                           endpoint='test', request_id='request-43')
    assert 'ValueError' not in caplog.text
    error = RuntimeError('cycle')
    error.__cause__ = error
    log_import_failure(logging.getLogger(__name__), error,
                       endpoint='test', request_id='request-44')
    assert 'request-44' in caplog.text
