"""Atomic Phase 5 staging commit contract and transaction tests."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4, uuid5

import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from oldap_api.imports.authorization import AuthorizedTarget
from oldap_api.imports.capabilities import UploadCapabilityIssuer
from oldap_api.imports.commit import validate_import_commit
from oldap_api.imports.domain import (
    ImportClaimConflict,
    ImportJob,
    ImportState,
    ImportTask,
    TargetSnapshot,
)
from oldap_api.imports.repository import (
    GraphDbImportJobRepository,
    InMemoryImportJobRepository,
    _admin_create_query,
)
from oldap_api.imports.service import ImportJobService

IMPORT_ID = "11111111-1111-4111-8111-111111111111"
CLAIM_ID = "22222222-2222-4222-8222-222222222222"
MANIFEST_SHA256 = "a" * 64


class Authorizer:
    def authorize_target(self, connection, **kwargs):
        return AuthorizedTarget(_target(), 3_000_000_000)


def _target() -> TargetSnapshot:
    return TargetSnapshot(
        project_short_name="fasnacht",
        staging_area_iri="https://example.org/staging/area",
        staging_area_name="Area",
        target_root_folder_iri="https://example.org/staging/root",
        target_root_folder_name="Root",
    )


def _job() -> ImportJob:
    current = datetime.now(UTC)
    return ImportJob(
        import_id=IMPORT_ID,
        state=ImportState.IMPORTING,
        state_version=4,
        created_at=current - timedelta(hours=1),
        updated_at=current,
        requested_by_iri="https://example.org/users/alice",
        requested_by_user_id="alice",
        target=_target(),
        original_file_name="archive.zip",
        declared_compressed_size_bytes=1_000,
        actual_compressed_size_bytes=1_000,
        extracted_size_bytes=2_000,
        quota_reserved_bytes=2_000,
        manifest_sha256=MANIFEST_SHA256,
        active_claim_id=CLAIM_ID,
        active_claim_task=ImportTask.IMPORT.value,
        active_claim_worker_id="worker-1",
        active_claimed_at=current,
        active_claim_lease_expires_at=current + timedelta(minutes=5),
    )


def _payload(*, event_id: str | None = None) -> dict:
    namespace = UUID(IMPORT_ID)
    return {
        "eventId": event_id or str(uuid4()),
        "claimId": CLAIM_ID,
        "expectedStateVersion": 4,
        "manifestSha256": MANIFEST_SHA256,
        "folders": [
            {
                "entryIndex": 0,
                "relativePath": "Fotos",
                "parentRelativePath": "",
                "name": "Fotos",
            }
        ],
        "media": [
            {
                "entryIndex": 1,
                "relativePath": "Fotos/Bild.jpg",
                "parentRelativePath": "Fotos",
                "assetId": str(uuid5(namespace, "entry:1")),
                "checksumSha256": "b" * 64,
                "originalName": "Bild.jpg",
                "originalMimeType": "image/jpeg",
                "dctermsType": "dcmitype:StillImage",
                "protocol": "iiif",
                "derivativeName": "master.tif",
                "storagePath": "fasnacht/image",
            }
        ],
    }


def _service(repository) -> ImportJobService:
    return ImportJobService(
        repository,
        Authorizer(),
        UploadCapabilityIssuer(
            secret="commit-test-upload-secret-at-least-thirty-two-bytes"
        ),
    )


def test_commit_finishes_job_once_and_replays_the_exact_mapping() -> None:
    repository = InMemoryImportJobRepository()
    repository.create(_job(), quota_limit_bytes=3_000_000_000)
    service = _service(repository)
    payload = _payload()

    imported, event_id, resources = service.commit_import(IMPORT_ID, payload)
    replay, replay_event, replay_resources = service.commit_import(IMPORT_ID, payload)

    assert imported.state is ImportState.IMPORTED
    assert imported.state_version == 5
    assert imported.imported_at is not None
    assert imported.cleanup_pending is True
    assert imported.active_claim_id is None
    assert event_id == replay_event == payload["eventId"]
    assert resources == replay_resources == imported.imported_resources
    assert [resource["entryIndex"] for resource in resources] == [0, 1]
    assert replay == imported


def test_commit_rejects_stale_claim_and_untrusted_asset_mapping() -> None:
    repository = InMemoryImportJobRepository()
    repository.create(_job(), quota_limit_bytes=3_000_000_000)
    service = _service(repository)

    with pytest.raises(ImportClaimConflict):
        service.commit_import(
            IMPORT_ID,
            _payload() | {"claimId": "33333333-3333-4333-8333-333333333333"},
        )
    bad = _payload()
    bad["media"][0]["assetId"] = str(uuid4())
    with pytest.raises(ValueError, match="identity"):
        service.commit_import(IMPORT_ID, bad)


def test_compensated_import_failure_is_terminal_and_exactly_replayable() -> None:
    repository = InMemoryImportJobRepository()
    repository.create(_job(), quota_limit_bytes=3_000_000_000)
    service = _service(repository)
    payload = {
        "eventId": "55555555-5555-4555-8555-555555555555",
        "claimId": CLAIM_ID,
        "expectedStateVersion": 4,
        "task": "IMPORT",
        "failureCode": "IMPORT_COMMIT_REJECTED",
        "compensated": True,
        "temporaryPayloadDeleted": True,
    }

    failed = service.fail_import(IMPORT_ID, payload)
    replay = service.fail_import(IMPORT_ID, payload)

    assert failed == replay
    assert failed.state is ImportState.FAILED
    assert failed.quota_reserved_bytes == 0
    assert failed.cleanup_pending is False
    assert failed.failure_code == "IMPORT_COMMIT_REJECTED"


class CommitConnection:
    """Script the live transaction checks and retain both atomic updates."""

    def __init__(self, job: ImportJob) -> None:
        self.job = job
        self.started = self.committed = self.aborted = 0
        self.updates: list[str] = []
        self.transaction_queries: list[str] = []

    def transaction_start(self):
        self.started += 1

    def transaction_query(self, query):
        self.transaction_queries.append(query)
        if "SELECT ?payload" in query:
            return {
                "results": {
                    "bindings": [
                        {
                            "payload": {
                                "value": json.dumps(self.job.to_dict(internal=True))
                            }
                        }
                    ]
                }
            }
        if "SELECT ?areaName" in query:
            return {
                "results": {
                    "bindings": [
                        {
                            "areaName": {"value": "Area"},
                            "folderName": {"value": "Root"},
                            "defaultRole": {
                                "value": "https://example.org/roles/staging"
                            },
                            "defaultPermission": {
                                "value": "http://oldap.org/base#DATA_UPDATE"
                            },
                        }
                    ]
                }
            }
        if "ADMIN_CREATE" in query:
            return {"boolean": True}
        if "SELECT ?kind ?name" in query:
            return {"results": {"bindings": []}}
        if "shared:assetId" in query:
            return {"boolean": False}
        raise AssertionError(query)

    def transaction_update(self, query):
        self.updates.append(query)

    def transaction_commit(self):
        self.committed += 1

    def transaction_abort(self):
        self.aborted += 1


def test_graphdb_resources_and_imported_job_share_one_transaction() -> None:
    job = _job()
    commit = validate_import_commit(IMPORT_ID, _payload(), "fasnacht")
    updated = replace(
        job,
        state=ImportState.IMPORTED,
        state_version=5,
        updated_at=datetime.now(UTC),
        active_claim_id=None,
        active_claim_task=None,
    )
    connection = CommitConnection(job)

    GraphDbImportJobRepository(
        connection,
        data_graph_resolver=lambda _connection, _short_name: URIRef(
            "https://fasnacht.digital/data"
        ),
        media_ingest_base_url="https://media.example.org",
    ).commit_import(job, updated, commit)

    assert connection.started == connection.committed == 1
    assert connection.aborted == 0
    assert len(connection.updates) == 2
    resource_insert, job_replace = connection.updates
    assert "shared:StagingFolder" in resource_insert
    assert "shared:StagingMediaObject" in resource_insert
    assert "shared:checksum" in resource_insert
    assert 'shared:serverUrl "https://media.example.org/iiif/3/"' in resource_insert
    assert "shared:StagingStatusNew" in resource_insert
    assert "oldap:attachedToRole" in resource_insert
    assert "XMLSchema#dateTimeStamp" in resource_insert
    assert "XMLSchema#dateTime>" not in resource_insert
    assert "GRAPH <https://fasnacht.digital/data>" in resource_insert
    assert "fasnacht:data" not in "\n".join(connection.updates)
    assert "PREFIX schema: <https://schema.org/>" in resource_insert
    target_query = next(
        query for query in connection.transaction_queries if "SELECT ?areaName" in query
    )
    assert "rdfs:subClassOf+ shared:StagingArea" in target_query
    assert "urn:oldap:importPayload" in job_replace


def test_commit_admin_check_uses_the_stored_project_short_name_datatype() -> None:
    """Match the xsd:NCName representation used by OLDAP's admin graph."""

    query = _admin_create_query(_job())

    assert Literal("fasnacht", datatype=XSD.NCName).n3() in query
