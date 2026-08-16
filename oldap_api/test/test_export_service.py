"""Application-service tests for public project-neutral ZIP exports."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from oldap_api.exports.capabilities import ExportDownloadCapabilityIssuer
from oldap_api.exports.domain import (
    ExportKind,
    ExportSelectionSnapshot,
    ExportState,
    ExportVersionConflict,
)
from oldap_api.exports.manifest import ExportManifest
from oldap_api.exports.profiles import (
    FileExportProfileRegistry,
    parse_export_profile,
)
from oldap_api.exports.repository import (
    ExportNotFoundError,
    ExportQuotaExceededError,
    InMemoryExportJobRepository,
)
from oldap_api.exports.service import (
    ExportJobService,
    ExportPermissionDeniedError,
    ExportValidationError,
)
from oldap_api.exports.staging_snapshot import ExportSnapshot
from oldap_api.exports.snapshot_router import ExportSnapshotRouter
from oldap_api.exports.settings import ExportOperatingPolicy

NOW = datetime(2026, 8, 14, 23, 0, tzinfo=UTC)
AREA = "urn:uuid:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
EXPORT_IDS = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
    "33333333-3333-4333-8333-333333333333",
)
DOWNLOAD_SECRET = "export-download-service-test-secret-at-least-32-bytes"


def _profile():
    return parse_export_profile(
        {
            "profileId": "museum-v1",
            "profileVersion": "1.0.0",
            "projectShortName": "museum",
            "allowedArchiveMediaClasses": ["museum:DigitalSurrogate"],
            "metadata": {
                "archiveMedia": [],
                "archiveUnits": [],
                "stagingMedia": [],
            },
        }
    )


class FakeProfileRegistry:
    def get_active(self, project_short_name):
        assert project_short_name == "museum"
        return _profile()


class FakeProjector:
    def __init__(self, source_bytes: int = 0) -> None:
        self.calls = []
        self.source_bytes = source_bytes

    def project(self, connection, **kwargs):
        self.calls.append((connection, kwargs))
        profile = kwargs["profile"]
        selection = ExportSelectionSnapshot(
            project_short_name=profile.project_short_name,
            kind=kwargs["kind"],
            selection_iri=kwargs["selection_iri"],
            display_name="Museum Staging",
            display_path="Museum Staging",
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            profile_sha256="a" * 64,
        )
        manifest_selection = {
            "displayName": "Museum Staging",
            "displayPath": "Museum Staging",
        }
        if kwargs["selection_iri"] is not None:
            manifest_selection["iri"] = kwargs["selection_iri"]
        manifest_value = {
            "documentType": "oldap.zip-export.manifest",
            "schemaVersion": "1.0.0",
            "exportId": kwargs["export_id"],
            "generatedAt": kwargs["generated_at"].isoformat().replace("+00:00", "Z"),
            "kind": kwargs["kind"].value,
            "projectShortName": profile.project_short_name,
            "requestedByIri": kwargs["requested_by_iri"],
            "profile": {
                "profileId": profile.profile_id,
                "profileVersion": profile.profile_version,
                "profileSha256": "a" * 64,
                "metadataSchemaVersion": "1.0.0",
            },
            "selection": manifest_selection,
            "limits": {"maxArchiveBytes": 50_000_000_000},
            "directories": [],
            "media": (
                [
                    {
                        "entryIndex": 0,
                        "relativePath": "Museum Staging/source.bin",
                        "mediaIri": "urn:uuid:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                        "containerIri": AREA,
                        "included": True,
                        "binarySource": {
                            "assetId": "quota-source",
                            "storagePath": "museum/quota/source.bin",
                            "originalName": "source.bin",
                            "originalMimeType": "application/octet-stream",
                            "expectedSizeBytes": self.source_bytes,
                        },
                        "metadata": {},
                    }
                ]
                if self.source_bytes
                else []
            ),
        }
        if kwargs["kind"] in {ExportKind.ARCHIVE_UNIT, ExportKind.ARCHIVE_ALL}:
            manifest_value["archiveUnits"] = []
        manifest = ExportManifest.from_dict(manifest_value)
        return ExportSnapshot(
            selection,
            manifest,
            1 if self.source_bytes else 0,
            self.source_bytes,
            0,
        )


class FakeDownloadAuthorizer:
    def __init__(self) -> None:
        self.calls = []

    def authorize(self, connection, **kwargs):
        self.calls.append((connection, kwargs))


def _connection(user_id="alice"):
    return SimpleNamespace(
        userid=user_id,
        userIri=f"https://example.org/users/{user_id}",
    )


def _body(kind="STAGING_ALL"):
    return {
        "projectShortName": "museum",
        "kind": kind,
        "selectionIri": AREA,
    }


def _service(repository=None, projector=None, policy=None):
    return ExportJobService(
        repository or InMemoryExportJobRepository(),
        profile_registry=FakeProfileRegistry(),
        snapshot_projector=projector or FakeProjector(),
        operating_policy=policy,
    )


def _policy(**overrides) -> ExportOperatingPolicy:
    values = {
        "max_archive_bytes": 50_000_000_000,
        "ready_retention_hours": 24,
        "audit_retention_days": 60,
        "max_active_jobs_per_user": 3,
        "max_active_jobs_total": 20,
        "max_reserved_bytes_per_user": 100_000_000_000,
        "max_reserved_bytes_total": 500_000_000_000,
    }
    values.update(overrides)
    return ExportOperatingPolicy(**values)


def test_estimate_is_read_only_and_create_atomically_publishes_snapshot() -> None:
    repository = InMemoryExportJobRepository()
    projector = FakeProjector()
    service = _service(repository, projector)
    connection = _connection()

    estimate = service.estimate(connection, _body(), now=NOW)
    assert estimate["filesTotal"] == 0
    assert repository.list_for_user(connection.userIri) == ()
    assert projector.calls[0][1]["enforce_size_limit"] is False

    job = service.create(
        connection,
        _body(),
        now=NOW,
        export_id=EXPORT_IDS[0],
    )
    assert job.state is ExportState.QUEUED
    assert job.snapshot_at == NOW
    assert repository.get(EXPORT_IDS[0]) == job
    assert repository.get_manifest(EXPORT_IDS[0]).sha256 == job.manifest_sha256
    assert projector.calls[1][1]["enforce_size_limit"] is True


def test_creation_reserves_active_job_and_retained_byte_quotas() -> None:
    repository = InMemoryExportJobRepository()
    service = _service(
        repository,
        FakeProjector(source_bytes=60),
        _policy(
            max_active_jobs_per_user=1,
            max_active_jobs_total=2,
            max_reserved_bytes_per_user=100,
            max_reserved_bytes_total=200,
        ),
    )
    alice = _connection()
    service.create(alice, _body(), now=NOW, export_id=EXPORT_IDS[0])

    with pytest.raises(ExportQuotaExceededError, match="active export-job"):
        service.create(
            alice,
            _body(),
            now=NOW + timedelta(seconds=1),
            export_id=EXPORT_IDS[1],
        )

    bob_service = _service(
        repository,
        FakeProjector(source_bytes=150),
        _policy(
            max_active_jobs_per_user=1,
            max_active_jobs_total=2,
            max_reserved_bytes_per_user=150,
            max_reserved_bytes_total=200,
        ),
    )
    with pytest.raises(ExportQuotaExceededError, match="system retained"):
        bob_service.create(
            _connection("bob"),
            _body(),
            now=NOW + timedelta(seconds=2),
            export_id=EXPORT_IDS[2],
        )


def test_concurrent_creation_cannot_overbook_the_per_user_job_quota() -> None:
    service = _service(
        policy=_policy(max_active_jobs_per_user=1, max_active_jobs_total=2)
    )
    alice = _connection()

    def create(export_id: str):
        try:
            return service.create(alice, _body(), now=NOW, export_id=export_id)
        except ExportQuotaExceededError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(create, EXPORT_IDS[:2]))

    assert sum(isinstance(result, ExportQuotaExceededError) for result in results) == 1
    assert sum(not isinstance(result, Exception) for result in results) == 1


def test_snapshot_router_dispatches_staging_and_archive_kinds() -> None:
    staging = FakeProjector()
    archive = FakeProjector()
    router = ExportSnapshotRouter(staging, archive)
    connection = _connection()
    common = {
        "export_id": EXPORT_IDS[0],
        "project_short_name": "museum",
        "requested_by_iri": connection.userIri,
        "selection_iri": AREA,
        "profile": _profile(),
        "generated_at": NOW,
    }

    router.project(connection, kind=ExportKind.STAGING_ALL, **common)
    router.project(connection, kind=ExportKind.ARCHIVE_UNIT, **common)

    assert len(staging.calls) == 1
    assert staging.calls[0][1]["kind"] is ExportKind.STAGING_ALL
    assert len(archive.calls) == 1
    assert archive.calls[0][1]["kind"] is ExportKind.ARCHIVE_UNIT


def test_anonymous_and_open_requests_are_rejected_and_archive_is_available() -> None:
    service = _service()
    with pytest.raises(ExportPermissionDeniedError):
        service.estimate(_connection("unknown"), _body(), now=NOW)
    archive = service.estimate(_connection(), _body("ARCHIVE_UNIT"), now=NOW)
    assert archive["kind"] == "ARCHIVE_UNIT"
    archive_all = service.estimate(
        _connection(),
        {"projectShortName": "museum", "kind": "ARCHIVE_ALL"},
        now=NOW,
    )
    assert archive_all["kind"] == "ARCHIVE_ALL"
    with pytest.raises(ExportValidationError):
        service.estimate(_connection(), _body("ARCHIVE_ALL"), now=NOW)
    with pytest.raises(ExportValidationError):
        service.estimate(_connection(), _body() | {"unexpected": True}, now=NOW)
    with pytest.raises(ExportValidationError):
        service.estimate(_connection(), _body() | {"includeTrash": True}, now=NOW)


def test_oldap_qname_selection_is_accepted_without_weakening_iri_validation() -> None:
    projector = FakeProjector()
    service = _service(projector=projector)

    service.estimate(
        _connection(),
        {
            "projectShortName": "museum",
            "kind": "ARCHIVE_UNIT",
            "selectionIri": "museum:posters",
        },
        now=NOW,
    )

    assert projector.calls[0][1]["selection_iri"] == "museum:posters"
    with pytest.raises(ExportValidationError):
        service.estimate(
            _connection(),
            _body() | {"selectionIri": "museum:../posters"},
            now=NOW,
        )


def test_owner_visibility_cursor_and_optimistic_delete() -> None:
    repository = InMemoryExportJobRepository()
    service = _service(repository)
    alice = _connection()
    for index, export_id in enumerate(EXPORT_IDS):
        service.create(
            alice,
            _body(),
            now=NOW + timedelta(seconds=index),
            export_id=export_id,
        )

    first = service.list_for_user(alice, limit=2)
    second = service.list_for_user(alice, limit=2, cursor=first.next_cursor)
    assert len(first.items) == 2
    assert first.next_cursor is not None
    assert len(second.items) == 1
    assert second.next_cursor is None
    with pytest.raises(ExportValidationError):
        service.list_for_user(alice, cursor="invalid")
    with pytest.raises(ExportNotFoundError):
        service.get_for_user(EXPORT_IDS[0], _connection("bob"))

    cancelled = service.delete(EXPORT_IDS[0], alice, expected_state_version=0, now=NOW)
    assert cancelled.state is ExportState.CANCELLED
    with pytest.raises(ExportVersionConflict):
        service.delete(EXPORT_IDS[0], alice, expected_state_version=0, now=NOW)
    deleting = service.delete(EXPORT_IDS[0], alice, expected_state_version=1, now=NOW)
    assert deleting.state is ExportState.DELETING


def test_download_rechecks_manifest_sources_and_issues_owner_capability() -> None:
    repository = InMemoryExportJobRepository()
    creation = _service(repository)
    connection = _connection()
    queued = creation.create(connection, _body(), now=NOW, export_id=EXPORT_IDS[0])
    building = queued.transition(
        ExportState.BUILDING,
        expected_state_version=0,
        now=NOW + timedelta(minutes=1),
    )
    repository.save(building, expected_previous_version=0)
    ready = building.transition(
        ExportState.READY,
        expected_state_version=1,
        now=NOW + timedelta(minutes=2),
        ready_at=NOW + timedelta(minutes=2),
        expires_at=NOW + timedelta(hours=24),
        archive_size_bytes=100,
        archive_sha256="b" * 64,
    )
    repository.save(ready, expected_previous_version=1)
    authorizer = FakeDownloadAuthorizer()
    service = ExportJobService(
        repository,
        capability_issuer=ExportDownloadCapabilityIssuer(
            secret=DOWNLOAD_SECRET,
            media_export_base_url="https://media.example.org",
        ),
        download_authorizer=authorizer,
    )

    authorization = service.issue_download_capability(
        ready.export_id, connection, now=NOW + timedelta(minutes=3)
    )
    assert f"/exports/{ready.export_id}/archive?token=" in authorization.url
    assert len(authorizer.calls) == 1
    assert authorizer.calls[0][1]["job"] == ready


def test_bundled_fasnacht_profile_matches_the_documented_contract() -> None:
    profile = FileExportProfileRegistry.from_environment().get_active("fasnacht")
    documented = Path(__file__).resolve().parents[2] / (
        "doc/zip-export/v1/examples/fasnacht-v1.profile.json"
    )
    import json

    assert profile.to_dict() == json.loads(documented.read_text(encoding="utf-8"))
