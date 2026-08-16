"""Cross-system ZIP export tests joining the API lifecycle to the physical worker."""

from __future__ import annotations

import csv
import hashlib
import io
import os
import sys
import zipfile
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

MEDIA_SOURCE = Path(__file__).resolve().parents[3] / "oldap-mediaserver" / "mediaserver"
if str(MEDIA_SOURCE) not in sys.path:
    sys.path.insert(0, str(MEDIA_SOURCE))

from export_artifacts import ExportArtifactStore  # noqa: E402
from export_service import BuildClaim, CleanupClaim  # noqa: E402
from export_worker import ExportWorkerSettings, SequentialExportWorker  # noqa: E402
from storage_capacity import DiskUsage, StorageCapacityGuard  # noqa: E402

from oldap_api.exports.domain import (  # noqa: E402
    ExportJob,
    ExportKind,
    ExportProgress,
    ExportSelectionSnapshot,
    ExportState,
    ExportTask,
)
from oldap_api.exports.manifest import ExportManifest  # noqa: E402
from oldap_api.exports.repository import InMemoryExportJobRepository  # noqa: E402
from oldap_api.exports.service import ExportJobService  # noqa: E402
from oldap_api.exports.worker_service import ExportWorkerService  # noqa: E402


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _job_and_manifest(
    source: Path,
    content: bytes,
    *,
    export_id: str | None = None,
    archive: bool = False,
) -> tuple[ExportJob, ExportManifest]:
    identifier = export_id or str(uuid4())
    now = datetime.now(UTC)
    relative_source = source.relative_to(source.parents[2]).as_posix()
    checksum = hashlib.sha256(content).hexdigest()
    manifest_value = {
        "documentType": "oldap.zip-export.manifest",
        "schemaVersion": "1.0.0",
        "exportId": identifier,
        "generatedAt": _timestamp(now),
        "kind": "ARCHIVE_UNIT" if archive else "STAGING_FOLDER",
        "projectShortName": "museum",
        "requestedByIri": "https://example.org/users/alice",
        "profile": {
            "profileId": "museum-v1",
            "profileVersion": "1.0.0",
            "profileSha256": "a" * 64,
            "metadataSchemaVersion": "1.0.0",
        },
        "selection": {
            "iri": "urn:uuid:22222222-2222-4222-8222-222222222222",
            "displayName": "Phase 1 acceptance",
            "displayPath": "Museum/Phase 1 acceptance",
        },
        "limits": {"maxArchiveBytes": 50_000_000_000},
        "directories": [
            {
                "relativePath": "Phase 1 acceptance/Empty",
                "containerIri": "urn:uuid:22222222-2222-4222-8222-222222222222",
            }
        ],
        "media": [
            {
                "entryIndex": 0,
                "relativePath": f"Phase 1 acceptance/{source.name}",
                "mediaIri": "urn:uuid:33333333-3333-4333-8333-333333333333",
                "containerIri": "urn:uuid:22222222-2222-4222-8222-222222222222",
                "included": True,
                "binarySource": {
                    "assetId": "phase-1-source",
                    "storagePath": relative_source,
                    "originalName": source.name,
                    "originalMimeType": "application/octet-stream",
                    "expectedSizeBytes": len(content),
                    "recordedChecksum": checksum,
                },
                "metadata": {"title": {"de": "Abnahme"}},
            }
        ],
    }
    if archive:
        manifest_value["directories"] = [
            {
                "relativePath": "Phase 1 acceptance",
                "containerIri": "urn:uuid:22222222-2222-4222-8222-222222222222",
            }
        ]
        manifest_value["archiveUnits"] = [
            {
                "relativePath": "Phase 1 acceptance",
                "unitIri": "urn:uuid:22222222-2222-4222-8222-222222222222",
                "archiveLevelIri": "shared:Fonds",
                "identifier": "MUS-P",
                "title": {"de": "Plakate"},
                "description": {"de": "Physische Phase-2-Abnahme"},
                "temporal": "1900 - 1999",
                "materialExtent": {"de": "1 Datei"},
                "creatorIris": ["https://example.org/agents/curator"],
                "provenance": {},
                "conditionsOfAccess": {},
                "metadata": {"catalogue_note": "Reviewed"},
            }
        ]
    manifest = ExportManifest.from_dict(manifest_value)
    selection = ExportSelectionSnapshot(
        project_short_name="museum",
        kind=ExportKind.ARCHIVE_UNIT if archive else ExportKind.STAGING_FOLDER,
        selection_iri="urn:uuid:22222222-2222-4222-8222-222222222222",
        display_name="Phase 1 acceptance",
        display_path="Museum/Phase 1 acceptance",
        profile_id="museum-v1",
        profile_version="1.0.0",
        profile_sha256="a" * 64,
    )
    return (
        ExportJob(
            export_id=identifier,
            state=ExportState.QUEUED,
            state_version=0,
            created_at=now,
            updated_at=now,
            requested_by_iri="https://example.org/users/alice",
            requested_by_user_id="alice",
            selection=selection,
            estimated_source_bytes=len(content),
            progress=ExportProgress(files_total=1, bytes_total=len(content)),
            snapshot_at=now,
            manifest_sha256=manifest.sha256,
        ),
        manifest,
    )


@dataclass
class DirectWorkerClient:
    """Adapt the real API worker service to the media worker protocol."""

    service: ExportWorkerService
    lease_seconds: int = 300
    cleanup_reasons: list[str] = field(default_factory=list)

    def validate_configuration(self) -> None:
        return None

    def claim_next(self) -> BuildClaim | CleanupClaim | None:
        claim = self.service.claim_next(
            {
                "workerId": "phase-1-acceptance",
                "supportedTasks": ["BUILD", "CLEANUP"],
                "requestedLeaseSeconds": self.lease_seconds,
            }
        )
        if claim is None:
            return None
        if claim.task is ExportTask.BUILD:
            return BuildClaim(
                claim.claim_id,
                claim.export_id,
                claim.state_version,
                claim.claimed_at,
                claim.lease_expires_at,
                claim.manifest_sha256 or "",
            )
        self.cleanup_reasons.append(claim.cleanup_reason or "")
        return CleanupClaim(
            claim.claim_id,
            claim.export_id,
            claim.state_version,
            claim.claimed_at,
            claim.lease_expires_at,
            claim.cleanup_reason or "",
        )

    def heartbeat(self, claim: BuildClaim | CleanupClaim) -> datetime:
        _, renewed_until = self.service.heartbeat_claim(
            claim.claim_id,
            {
                "workerId": "phase-1-acceptance",
                "expectedStateVersion": claim.state_version,
            },
        )
        return renewed_until

    def get_manifest(self, claim: BuildClaim) -> dict[str, object]:
        return self.service.manifest_for_claim(
            claim.export_id,
            claim.claim_id,
        ).to_dict()

    def publish_build_result(
        self,
        claim: BuildClaim,
        result: dict[str, object],
    ) -> None:
        self.service.record_build_result(claim.export_id, result)

    def publish_cleanup_result(
        self,
        claim: CleanupClaim,
        result: dict[str, object],
    ) -> None:
        self.service.record_cleanup_result(claim.export_id, result)


def _acceptance_runtime(tmp_path: Path, content: bytes, *, archive: bool = False):
    media_root = tmp_path / "media"
    source = media_root / "museum" / "original" / "source.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(content)
    export_root = tmp_path / "exports"
    export_root.mkdir()
    job, manifest = _job_and_manifest(source, content, archive=archive)
    repository = InMemoryExportJobRepository()
    repository.create_with_manifest(job, manifest)
    service = ExportWorkerService(repository)
    client = DirectWorkerClient(service)
    store = ExportArtifactStore(
        export_root,
        media_root,
        capacity_guard=StorageCapacityGuard(
            disk_usage=lambda path: DiskUsage(100_000_000_000, 0, 100_000_000_000)
        ),
    )
    worker = SequentialExportWorker(
        client,
        ExportWorkerSettings(media_root, export_root, 0.01, 60),
        store=store,
    )
    return source, export_root, job, repository, service, client, worker


def test_archive_export_reaches_ready_with_archive_inventory_csv(
    tmp_path: Path,
) -> None:
    """Exercise the API lifecycle and ontology-blind worker for an ArchiveUnit ZIP."""

    payload = b"phase-2 archive original"
    _, export_root, job, repository, _, _, worker = _acceptance_runtime(
        tmp_path, payload, archive=True
    )

    assert worker.run_once() is True
    ready = repository.get(job.export_id)
    archive_path = export_root / job.export_id / "archive.zip"
    assert ready.state is ExportState.READY
    assert archive_path.is_file()
    with zipfile.ZipFile(archive_path) as archive_file:
        assert archive_file.read("Phase 1 acceptance/source.bin") == payload
        assert {
            "README.txt",
            "export.csv",
            "metadata.csv",
            "archive-units.csv",
        } <= set(archive_file.namelist())
        raw = archive_file.read("archive-units.csv")
        assert raw.startswith(b"\xef\xbb\xbf")
        rows = list(csv.DictReader(io.StringIO(raw[3:].decode("utf-8"))))
        assert len(rows) == 1
        assert rows[0]["unit_iri"] == ("urn:uuid:22222222-2222-4222-8222-222222222222")
        assert rows[0]["identifier"] == "MUS-P"
        assert rows[0]["catalogue_note"] == "Reviewed"


@pytest.mark.parametrize(
    "content",
    [b"small phase-1 export", pytest.param(None, id="32MiB")],
)
def test_small_and_large_exports_reach_ready_with_verifiable_zip(
    tmp_path: Path,
    content: bytes | None,
) -> None:
    payload = content if content is not None else os.urandom(32 * 1024 * 1024)
    _, export_root, job, repository, service, _, worker = _acceptance_runtime(
        tmp_path, payload
    )

    assert worker.run_once() is True
    ready = repository.get(job.export_id)
    archive_path = export_root / job.export_id / "archive.zip"
    assert ready.state is ExportState.READY
    assert archive_path.is_file()
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == ready.archive_sha256
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.read("Phase 1 acceptance/source.bin") == payload
        assert "Phase 1 acceptance/Empty/" in archive.namelist()
        assert {"README.txt", "export.csv", "metadata.csv"} <= set(archive.namelist())

    notified = service.record_notification_result(ready.export_id, success=True)
    assert notified.notification_status.value == "SENT"


def test_failed_source_is_cleaned_without_exposing_partial_artifact(
    tmp_path: Path,
) -> None:
    source, export_root, job, repository, _, client, worker = _acceptance_runtime(
        tmp_path, b"expected source"
    )
    source.write_bytes(b"changed after snapshot")

    assert worker.run_once() is True
    assert repository.get(job.export_id).state is ExportState.FAILED
    assert not (export_root / job.export_id).exists()
    assert worker.run_once() is True
    assert repository.get(job.export_id).state is ExportState.DELETED
    assert client.cleanup_reasons == ["FAILED"]


def test_manual_deletion_physically_removes_ready_archive(tmp_path: Path) -> None:
    _, export_root, job, repository, _, client, worker = _acceptance_runtime(
        tmp_path, b"manual deletion"
    )
    assert worker.run_once() is True
    ready = repository.get(job.export_id)
    assert (export_root / job.export_id / "archive.zip").is_file()

    owner = type(
        "Connection",
        (),
        {"userIri": "https://example.org/users/alice", "userid": "alice"},
    )()
    deleting = ExportJobService(repository).delete(
        job.export_id,
        owner,
        expected_state_version=ready.state_version,
    )
    assert deleting.state is ExportState.DELETING
    assert worker.run_once() is True
    assert repository.get(job.export_id).state is ExportState.DELETED
    assert not (export_root / job.export_id).exists()
    assert client.cleanup_reasons == ["READY_DELETE"]


def test_expiry_reconciliation_physically_removes_ready_archive(
    tmp_path: Path,
) -> None:
    _, export_root, job, repository, _, client, worker = _acceptance_runtime(
        tmp_path, b"expiry deletion"
    )

    assert worker.run_once() is True
    ready = repository.get(job.export_id)
    assert ready.state is ExportState.READY
    assert (export_root / job.export_id / "archive.zip").is_file()
    repository.save(
        replace(
            ready,
            state_version=ready.state_version + 1,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        ),
        expected_previous_version=ready.state_version,
    )
    assert worker.run_once() is True
    assert repository.get(job.export_id).state is ExportState.DELETED
    assert not (export_root / job.export_id).exists()
    assert client.cleanup_reasons == ["EXPIRED"]
