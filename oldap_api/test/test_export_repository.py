"""Durable GraphDB persistence tests for project-neutral ZIP exports."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from oldap_api.exports.domain import (
    ExportJob,
    ExportKind,
    ExportNotificationStatus,
    ExportProgress,
    ExportSelectionSnapshot,
    ExportState,
    ExportTask,
)
from oldap_api.exports.repository import (
    ExportAlreadyExistsError,
    ExportQuotaExceededError,
    ExportRepositoryConflict,
    GraphDbExportJobRepository,
)
from oldap_api.exports.settings import ExportOperatingPolicy
from oldap_api.test.test_export_manifest import bound_job

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
SHA = "a" * 64


def _job() -> ExportJob:
    """Return one complete queued job suitable for persistence tests."""

    return ExportJob(
        export_id="11111111-1111-4111-8111-111111111111",
        state=ExportState.QUEUED,
        state_version=0,
        created_at=NOW,
        updated_at=NOW,
        requested_by_iri="https://example.org/users/alice",
        requested_by_user_id="alice",
        selection=ExportSelectionSnapshot(
            project_short_name="museum",
            kind=ExportKind.ARCHIVE_UNIT,
            selection_iri="urn:uuid:22222222-2222-4222-8222-222222222222",
            display_name="Posters",
            display_path="Collection/Posters",
            profile_id="museum-v1",
            profile_version="1.0.0",
            profile_sha256=SHA,
        ),
        estimated_source_bytes=12_345,
        progress=ExportProgress(files_total=2, bytes_total=12_345),
        snapshot_at=NOW,
        manifest_sha256=SHA,
    )


class FakeTransactionalConnection:
    """Expose one canonical persisted job and record transaction boundaries."""

    def __init__(
        self,
        job: ExportJob,
        *,
        exists: bool = False,
        manifest=None,
        stored_manifest_sha256: str | None = None,
    ) -> None:
        self.job = job
        self.exists = exists
        self.manifest = manifest
        self.stored_manifest_sha256 = stored_manifest_sha256
        self.started = 0
        self.committed = 0
        self.aborted = 0
        self.updates: list[str] = []
        self.queries: list[str] = []

    def query(self, query):
        self.queries.append(query)
        if "urn:oldap:exportManifestPayload" in query:
            if self.manifest is None:
                return {"results": {"bindings": []}}
            return {
                "results": {
                    "bindings": [
                        {
                            "payload": {
                                "value": self.manifest.canonical_json.decode("utf-8")
                            },
                            "sha256": {
                                "value": self.stored_manifest_sha256
                                or self.manifest.sha256
                            },
                        }
                    ]
                }
            }
        return self._job_result()

    def transaction_start(self):
        self.started += 1

    def transaction_query(self, query):
        self.queries.append(query)
        if "ASK" in query:
            return {"boolean": self.exists}
        return self._job_result()

    def transaction_update(self, query):
        self.updates.append(query)

    def transaction_commit(self):
        self.committed += 1

    def transaction_abort(self):
        self.aborted += 1

    def _job_result(self):
        return {
            "results": {
                "bindings": [
                    {
                        "payload": {"value": json.dumps(self.job.to_persisted_dict())},
                        "created": {"value": self.job.created_at.isoformat()},
                    }
                ]
            }
        }


def test_internal_job_contract_round_trips_all_durable_fields():
    original = _job()

    persisted = original.to_persisted_dict()
    restored = ExportJob.from_dict(persisted)

    assert restored == original
    assert "canDownload" not in persisted
    assert "canDelete" not in persisted


def test_graphdb_create_is_atomic_and_stores_canonical_indexed_facts():
    connection = FakeTransactionalConnection(_job())
    repository = GraphDbExportJobRepository(connection)

    repository.create(_job())

    assert connection.started == 1
    assert connection.committed == 1
    assert connection.aborted == 0
    assert len(connection.updates) == 1
    update = connection.updates[0]
    assert "urn:oldap:export-jobs" in update
    assert "urn:oldap:exportOwner" in update
    assert "requestedByUserId" in update


def test_graphdb_create_aborts_instead_of_replacing_an_existing_uuid():
    connection = FakeTransactionalConnection(_job(), exists=True)
    repository = GraphDbExportJobRepository(connection)

    with pytest.raises(ExportAlreadyExistsError):
        repository.create(_job())

    assert connection.committed == 0
    assert connection.aborted == 1
    assert connection.updates == []


def test_graphdb_save_compares_and_updates_inside_one_transaction():
    connection = FakeTransactionalConnection(_job())
    repository = GraphDbExportJobRepository(connection)
    building = _job().transition(
        ExportState.BUILDING,
        expected_state_version=0,
        now=NOW + timedelta(minutes=1),
    )

    repository.save(building, expected_previous_version=0)

    assert connection.started == 1
    assert connection.committed == 1
    assert connection.aborted == 0
    assert len(connection.updates) == 1
    assert "urn:oldap:exportStateVersion" in connection.updates[0]
    assert "BUILDING" in connection.updates[0]


def test_graphdb_save_aborts_on_stale_persisted_version():
    persisted = _job().transition(
        ExportState.BUILDING,
        expected_state_version=0,
        now=NOW + timedelta(minutes=1),
    )
    connection = FakeTransactionalConnection(persisted)
    repository = GraphDbExportJobRepository(connection)

    with pytest.raises(ExportRepositoryConflict):
        repository.save(persisted, expected_previous_version=0)

    assert connection.committed == 0
    assert connection.aborted == 1
    assert connection.updates == []


def test_graphdb_expiry_transition_is_atomic_and_versioned():
    ready = replace(
        _job(),
        state=ExportState.READY,
        state_version=2,
        ready_at=NOW,
        expires_at=NOW + timedelta(hours=24),
        archive_size_bytes=123,
        archive_sha256="b" * 64,
    )
    connection = FakeTransactionalConnection(ready)
    repository = GraphDbExportJobRepository(connection)

    expired = repository.expire_next_ready(now=ready.expires_at)

    assert expired is not None
    assert expired.state is ExportState.EXPIRED
    assert expired.state_version == 3
    assert expired.cleanup_reason == "EXPIRED"
    assert connection.committed == 1
    assert "EXPIRED" in connection.updates[0]


def test_graphdb_notification_evidence_updates_without_lifecycle_version():
    current = replace(
        _job(),
        notification_status=ExportNotificationStatus.PENDING,
        notification_for_state=ExportState.FAILED,
    )
    updated = replace(
        current,
        notification_status=ExportNotificationStatus.FAILED,
        notification_attempts=1,
        notification_last_attempt_at=NOW,
        notification_last_error="SMTPException",
    )
    connection = FakeTransactionalConnection(current)
    repository = GraphDbExportJobRepository(connection)

    repository.update_notification(current, updated)

    assert updated.state_version == current.state_version
    assert connection.committed == 1
    assert "SMTPException" in connection.updates[0]


def test_graphdb_purges_only_due_content_free_audit_hulls():
    deleted = replace(
        _job(),
        state=ExportState.DELETED,
        deleted_at=NOW,
        audit_delete_at=NOW + timedelta(days=60),
        manifest_sha256=None,
    )
    connection = FakeTransactionalConnection(deleted)
    repository = GraphDbExportJobRepository(connection)

    assert repository.purge_expired_audits(now=deleted.audit_delete_at) == 1
    assert connection.committed == 1
    assert len(connection.updates) == 2
    assert all("DELETE WHERE" in update for update in connection.updates)


def test_graphdb_list_filters_owner_and_state_in_sparql():
    connection = FakeTransactionalConnection(_job())
    repository = GraphDbExportJobRepository(connection)

    jobs = repository.list_for_user(
        "https://example.org/users/alice", state=ExportState.QUEUED
    )

    assert jobs == (_job(),)
    query = connection.queries[-1]
    assert "https://example.org/users/alice" in query
    assert "urn:oldap:exportState" in query
    assert '"QUEUED"' in query


def test_graphdb_publishes_bound_job_and_manifest_in_one_insert():
    job, manifest = bound_job()
    connection = FakeTransactionalConnection(job, manifest=manifest)
    repository = GraphDbExportJobRepository(connection)

    repository.create_with_manifest(job, manifest)

    assert connection.started == 1
    assert connection.committed == 1
    assert connection.aborted == 0
    assert len(connection.updates) == 1
    update = connection.updates[0]
    assert "urn:oldap:ExportJob" in update
    assert "urn:oldap:ExportManifest" in update
    assert manifest.sha256 in update


def test_graphdb_checks_export_quota_inside_the_create_transaction():
    job, manifest = bound_job()
    existing = replace(
        job,
        export_id="99999999-9999-4999-8999-999999999999",
        manifest_sha256="f" * 64,
    )
    connection = FakeTransactionalConnection(existing)
    repository = GraphDbExportJobRepository(connection)
    policy = ExportOperatingPolicy(max_active_jobs_per_user=1)

    with pytest.raises(ExportQuotaExceededError, match="active export-job"):
        repository.create_with_manifest(job, manifest, operating_policy=policy)

    assert connection.started == 1
    assert connection.committed == 0
    assert connection.aborted == 1
    assert connection.updates == []


def test_graphdb_rejects_mismatched_manifest_before_starting_transaction():
    job, manifest = bound_job()
    connection = FakeTransactionalConnection(job, manifest=manifest)
    repository = GraphDbExportJobRepository(connection)

    with pytest.raises(ValueError, match="does not match"):
        repository.create_with_manifest(
            replace(job, manifest_sha256="f" * 64), manifest
        )

    assert connection.started == 0
    assert connection.updates == []


def test_graphdb_reads_and_verifies_immutable_manifest_digest():
    job, manifest = bound_job()
    connection = FakeTransactionalConnection(job, manifest=manifest)
    repository = GraphDbExportJobRepository(connection)

    assert repository.get_manifest(job.export_id) == manifest

    corrupt = FakeTransactionalConnection(
        job, manifest=manifest, stored_manifest_sha256="f" * 64
    )
    with pytest.raises(ExportRepositoryConflict, match="digest mismatch"):
        GraphDbExportJobRepository(corrupt).get_manifest(job.export_id)


def test_graphdb_claim_is_atomic_and_indexes_active_claim():
    connection = FakeTransactionalConnection(_job())
    repository = GraphDbExportJobRepository(connection)

    claimed = repository.claim_next(
        worker_id="worker-1",
        supported_tasks=(ExportTask.BUILD,),
        claim_id="33333333-3333-4333-8333-333333333333",
        claimed_at=NOW + timedelta(minutes=1),
        lease_expires_at=NOW + timedelta(minutes=6),
    )

    assert claimed is not None
    assert claimed.state is ExportState.BUILDING
    assert claimed.state_version == 1
    assert claimed.active_claim_lease_seconds == 300
    assert connection.committed == 1
    assert "urn:oldap:exportActiveClaim" in connection.updates[0]


def test_graphdb_cleanup_atomically_purges_manifest_payload():
    claimed_at = NOW + timedelta(minutes=1)
    current = replace(
        _job(),
        state=ExportState.DELETING,
        state_version=1,
        active_claim_id="44444444-4444-4444-8444-444444444444",
        active_claim_task=ExportTask.CLEANUP,
        active_claim_worker_id="worker-1",
        active_claimed_at=claimed_at,
        active_claim_lease_expires_at=claimed_at + timedelta(minutes=5),
        active_claim_lease_seconds=300,
        cleanup_reason="READY_DELETE",
    )
    deleted_at = claimed_at + timedelta(minutes=2)
    deleted = current.transition(
        ExportState.DELETED,
        expected_state_version=1,
        now=deleted_at,
        deleted_at=deleted_at,
        manifest_sha256=None,
        active_claim_id=None,
        active_claim_task=None,
        active_claim_worker_id=None,
        active_claimed_at=None,
        active_claim_lease_expires_at=None,
        active_claim_lease_seconds=None,
        cleanup_reason=None,
    )
    connection = FakeTransactionalConnection(current)

    GraphDbExportJobRepository(connection).complete_cleanup(current, deleted)

    assert connection.committed == 1
    assert len(connection.updates) == 2
    assert "DELETE WHERE" in connection.updates[1]
    assert "export-manifest" in connection.updates[1]
