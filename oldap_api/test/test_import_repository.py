"""Transaction-orchestration tests for the GraphDB import queue repository."""

import json
from datetime import UTC, datetime, timedelta

from oldap_api.imports.domain import ImportJob, ImportState, ImportTask, TargetSnapshot
from oldap_api.imports.repository import GraphDbImportJobRepository


def _job() -> ImportJob:
    current = datetime.now(UTC)
    return ImportJob(
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
            staging_area_name="Area",
            target_root_folder_iri="https://example.org/staging/root",
            target_root_folder_name="Root",
        ),
        original_file_name="archive.zip",
        declared_compressed_size_bytes=1_000_000,
        actual_compressed_size_bytes=1_000_000,
        quota_reserved_bytes=50_000_000,
        sip_sha256="a" * 64,
    )


class FakeTransactionalConnection:
    """Return a fixed queue snapshot and record the transaction boundary."""

    def __init__(self, job: ImportJob) -> None:
        self.job = job
        self.started = 0
        self.committed = 0
        self.aborted = 0
        self.updates: list[str] = []

    def transaction_start(self):
        self.started += 1

    def transaction_query(self, query):
        return {
            "results": {
                "bindings": [
                    {
                        "payload": {
                            "value": json.dumps(self.job.to_dict(internal=True))
                        },
                        "created": {"value": self.job.created_at.isoformat()},
                    }
                ]
            }
        }

    def transaction_update(self, query):
        self.updates.append(query)

    def transaction_commit(self):
        self.committed += 1

    def transaction_abort(self):
        self.aborted += 1


def test_graphdb_claim_selection_and_write_share_one_transaction():
    connection = FakeTransactionalConnection(_job())
    repository = GraphDbImportJobRepository(connection)
    current = datetime.now(UTC)

    claimed = repository.claim_next(
        worker_id="worker-1",
        supported_tasks=(ImportTask.VALIDATE,),
        claim_id="22222222-2222-4222-8222-222222222222",
        claimed_at=current,
        lease_expires_at=current + timedelta(minutes=5),
    )

    assert claimed is not None
    assert claimed.active_claim_task == "VALIDATE"
    assert claimed.state_version == 2
    assert connection.started == 1
    assert connection.committed == 1
    assert connection.aborted == 0
    assert len(connection.updates) == 1
    assert "urn:oldap:importActiveClaim" in connection.updates[0]


def test_graphdb_queue_does_not_write_while_an_unexpired_claim_exists():
    current = datetime.now(UTC)
    active = _job()
    active = ImportJob.from_dict(
        active.to_dict(internal=True)
        | {
            "activeClaimId": "33333333-3333-4333-8333-333333333333",
            "activeClaimTask": "VALIDATE",
            "activeClaimWorkerId": "worker-1",
            "activeClaimedAt": current.isoformat(),
            "activeClaimLeaseExpiresAt": (current + timedelta(minutes=5)).isoformat(),
        }
    )
    connection = FakeTransactionalConnection(active)
    repository = GraphDbImportJobRepository(connection)

    claimed = repository.claim_next(
        worker_id="worker-2",
        supported_tasks=(ImportTask.VALIDATE,),
        claim_id="44444444-4444-4444-8444-444444444444",
        claimed_at=current,
        lease_expires_at=current + timedelta(minutes=5),
    )

    assert claimed is None
    assert connection.committed == 1
    assert connection.updates == []
