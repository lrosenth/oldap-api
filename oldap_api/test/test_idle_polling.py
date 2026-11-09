"""Empty queues never start writes; stale eligibility hints never authorize writes."""

from dataclasses import replace
from datetime import timedelta

import pytest

from oldap_api.exports.domain import ExportState, ExportTask
from oldap_api.exports.repository import GraphDbExportJobRepository
from oldap_api.imports.domain import ImportTask
from oldap_api.imports.repository import GraphDbImportJobRepository
from oldap_api.mobile_media.lifecycle import GraphDbMobileMediaLifecycleOutbox
from oldap_api.test.test_export_repository import (
    FakeTransactionalConnection as ExportConnection,
    NOW,
    _job as export_job,
)
from oldap_api.test.test_import_repository import (
    FakeTransactionalConnection as ImportConnection,
    _job as import_job,
)
from oldap_api.test.test_mobile_media_lifecycle import (
    Connection,
    WORKER,
    _bindings,
    _claim_row,
)

EMPTY = {"results": {"bindings": []}}


def operation(kind):
    """Build real repository operations with valid eligible fixture payloads."""
    if kind == "import":
        job = import_job()
        connection = ImportConnection(job)
        repository = GraphDbImportJobRepository(connection)
        now = job.created_at
        invoke = lambda: repository.claim_next(
            worker_id="worker",
            supported_tasks=(ImportTask.VALIDATE,),
            claim_id="22222222-2222-4222-8222-222222222222",
            claimed_at=now,
            lease_expires_at=now + timedelta(minutes=5),
        )
    elif kind == "mobile":
        connection = Connection([_bindings([_claim_row()])])
        repository = GraphDbMobileMediaLifecycleOutbox(connection)
        invoke = lambda: repository.claim_next(WORKER, now=NOW)
    else:
        job = export_job()
        if kind == "expiry":
            job = replace(
                job,
                state=ExportState.READY,
                ready_at=NOW - timedelta(days=2),
                expires_at=NOW - timedelta(days=1),
                archive_size_bytes=123,
                archive_sha256="b" * 64,
            )
        elif kind == "purge":
            job = replace(
                job,
                state=ExportState.DELETED,
                deleted_at=NOW - timedelta(days=61),
                audit_delete_at=NOW - timedelta(days=1),
                manifest_sha256=None,
            )
        connection = ExportConnection(job)
        repository = GraphDbExportJobRepository(connection)
        if kind == "expiry":
            invoke = lambda: repository.expire_next_ready(now=NOW)
        elif kind == "purge":
            invoke = lambda: repository.purge_expired_audits(now=NOW)
        else:
            invoke = lambda: repository.claim_next(
                worker_id="worker",
                supported_tasks=(ExportTask.BUILD,),
                claim_id="22222222-2222-4222-8222-222222222222",
                claimed_at=NOW,
                lease_expires_at=NOW + timedelta(minutes=5),
            )
    return connection, invoke


@pytest.mark.parametrize("kind", ["import", "export", "expiry", "purge", "mobile"])
def test_empty_poll_never_reserves_transaction(kind):
    connection, invoke = operation(kind)
    connection.query = lambda query: EMPTY
    assert invoke() == (0 if kind == "purge" else None)
    assert connection.started == connection.committed == connection.aborted == 0
    assert connection.updates == []


@pytest.mark.parametrize("kind", ["import", "export", "expiry", "purge", "mobile"])
def test_candidate_taken_between_precheck_and_writer_lock(kind):
    connection, invoke = operation(kind)
    # A different worker wins after the hint. Every mutating path must reselect.
    if kind == "import":
        original = connection.transaction_query
        connection.query = original
    connection.transaction_query = lambda query: EMPTY
    assert invoke() == (0 if kind == "purge" else None)
    assert connection.started == connection.committed == 1
    assert connection.updates == []
