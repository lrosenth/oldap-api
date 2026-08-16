"""Authorized project-neutral Staging snapshot projection tests."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from oldap_api.exports.domain import ExportJob, ExportProgress, ExportState, ExportKind
from oldap_api.exports.profiles import parse_export_profile
from oldap_api.exports.staging_snapshot import (
    AuthorizedStagingInventory,
    ExportDownloadPermissionError,
    ExportSizeLimitError,
    ExportSnapshotError,
    LocalBinaryReference,
    OldapStagingInventoryReader,
    ResolvedBinarySource,
    StagingAreaRecord,
    StagingDownloadAuthorizer,
    StagingFolderRecord,
    StagingMediaRecord,
    StagingSnapshotProjector,
)
from oldap_api.exports import staging_snapshot
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName

NOW = datetime(2026, 8, 14, 16, 30, tzinfo=UTC)
EXPORT_ID = "11111111-1111-4111-8111-111111111111"
AREA = "urn:uuid:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TOP = "urn:uuid:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
FOLDER = "urn:uuid:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
CHILD = "urn:uuid:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
OTHER = "urn:uuid:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
TRASH = "urn:uuid:ffffffff-ffff-4fff-8fff-ffffffffffff"
TRASH_CHILD = "urn:uuid:12121212-1212-4212-8212-121212121212"


def profile():
    """Return one non-Fasnacht profile with a Staging metadata projection."""

    return parse_export_profile(
        {
            "profileId": "museum-v1",
            "profileVersion": "1.0.0",
            "projectShortName": "museum",
            "allowedArchiveMediaClasses": ["museum:DigitalSurrogate"],
            "metadata": {
                "archiveMedia": [],
                "archiveUnits": [],
                "stagingMedia": [
                    {
                        "columnName": "curatorial_note",
                        "propertyIri": "schema:comment",
                        "valueShape": "scalar",
                        "resolveLabels": False,
                    }
                ],
            },
        }
    )


def inventory() -> AuthorizedStagingInventory:
    """Return a visible tree containing normal, external, and Trash media."""

    return AuthorizedStagingInventory(
        area=StagingAreaRecord(AREA, "Museum Staging"),
        folders=(
            StagingFolderRecord(TOP, "top", None),
            StagingFolderRecord(FOLDER, "Posters", TOP),
            StagingFolderRecord(CHILD, "Portraits", FOLDER),
            StagingFolderRecord(OTHER, "Audio", TOP),
            StagingFolderRecord(TRASH, "Trash", TOP),
            StagingFolderRecord(TRASH_CHILD, "Deleted", TRASH),
        ),
        media=(
            _local_media("one", FOLDER, "One.jpg", 1),
            _local_media("two", CHILD, "Two.jpg", 2),
            _local_media("other", OTHER, "Other.wav", 3, mime="audio/wav"),
            _local_media("deleted", TRASH_CHILD, "Deleted.jpg", 4),
            StagingMediaRecord(
                iri="urn:uuid:99999999-9999-4999-8999-999999999999",
                folder_iri=FOLDER,
                access_mode="external",
                original_name="Provider image.jpg",
                original_mime_type="image/jpeg",
                external_source_url="https://images.example.org/full.jpg",
                metadata={"curatorial_note": "External"},
            ),
        ),
    )


def _local_media(
    suffix: str, folder: str, name: str, number: int, *, mime: str = "image/jpeg"
) -> StagingMediaRecord:
    return StagingMediaRecord(
        iri=f"urn:uuid:00000000-0000-4000-8000-{number:012d}",
        folder_iri=folder,
        access_mode="local",
        original_name=name,
        original_mime_type=mime,
        asset_id=f"asset-{suffix}",
        storage_path_candidate=f"museum/source/{suffix}",
        recorded_checksum=f"{number:x}" * 64,
        metadata={"curatorial_note": suffix.title()},
    )


class FakeBinaryResolver:
    """Confirm deterministic media facts and record the requested identities."""

    def __init__(self, sizes=None) -> None:
        self.sizes = sizes or {
            "asset-one": 5_000,
            "asset-two": 7_345,
            "asset-other": 9_000,
        }
        self.references: tuple[LocalBinaryReference, ...] = ()

    def resolve(self, references):
        self.references = references
        return {
            item.media_iri: ResolvedBinarySource(
                asset_id=item.asset_id,
                storage_path=f"museum/assets/{item.asset_id}/original/{item.original_name}",
                original_name=item.original_name,
                original_mime_type=(
                    "audio/wav" if item.original_name.endswith(".wav") else "image/jpeg"
                ),
                size_bytes=self.sizes[item.asset_id],
                sha256={
                    "asset-one": "1" * 64,
                    "asset-two": "2" * 64,
                    "asset-other": "3" * 64,
                    "asset-collision": "5" * 64,
                }[item.asset_id],
            )
            for item in references
        }


class FakeInventoryReader:
    def __init__(self, value):
        self.value = value
        self.call = None

    def read(self, connection, **kwargs):
        self.call = (connection, kwargs)
        return self.value


def test_folder_snapshot_preserves_subtree_and_excludes_other_and_trash():
    resolver = FakeBinaryResolver()
    projector = StagingSnapshotProjector(FakeInventoryReader(inventory()), resolver)

    snapshot = projector.project_inventory(
        export_id=EXPORT_ID,
        kind=ExportKind.STAGING_FOLDER,
        selection_iri=FOLDER,
        profile=profile(),
        generated_at=NOW,
        inventory=inventory(),
        requested_by_iri="https://example.org/users/alice",
    )

    assert snapshot.files_total == 2
    assert snapshot.source_bytes == 12_345
    assert snapshot.warning_count == 1
    value = snapshot.manifest.to_dict()
    assert [item["relativePath"] for item in value["directories"]] == [
        "Posters",
        "Posters/Portraits",
    ]
    assert [item["relativePath"] for item in value["media"]] == [
        "Posters/One.jpg",
        "Posters/Portraits/Two.jpg",
        "Posters/Provider image.jpg",
    ]
    assert {item.asset_id for item in resolver.references} == {
        "asset-one",
        "asset-two",
    }
    assert value["media"][2]["included"] is False
    assert value["media"][2]["exclusionReason"] == "EXTERNAL_ORIGINAL_UNAVAILABLE"

    job = ExportJob(
        export_id=EXPORT_ID,
        state=ExportState.QUEUED,
        state_version=0,
        created_at=NOW,
        updated_at=NOW,
        requested_by_iri="https://example.org/users/alice",
        requested_by_user_id="alice",
        selection=snapshot.selection,
        estimated_source_bytes=snapshot.source_bytes,
        warning_count=snapshot.warning_count,
        progress=ExportProgress(
            files_total=snapshot.files_total, bytes_total=snapshot.source_bytes
        ),
        snapshot_at=NOW,
        manifest_sha256=snapshot.manifest.sha256,
    )
    snapshot.manifest.validate_for_job(job)


def test_all_snapshot_uses_area_wrapper_and_omits_trash_subtree():
    resolver = FakeBinaryResolver()
    snapshot = StagingSnapshotProjector(
        FakeInventoryReader(inventory()), resolver
    ).project_inventory(
        export_id=EXPORT_ID,
        kind=ExportKind.STAGING_ALL,
        selection_iri=AREA,
        profile=profile(),
        generated_at=NOW,
        inventory=inventory(),
    )

    value = snapshot.manifest.to_dict()
    assert snapshot.files_total == 3
    assert snapshot.source_bytes == 21_345
    paths = {item["relativePath"] for item in value["media"]}
    assert "Museum Staging/Posters/One.jpg" in paths
    assert "Museum Staging/Audio/Other.wav" in paths
    assert not any("Trash" in path or "Deleted" in path for path in paths)
    assert snapshot.estimate_dict()["exceedsLimit"] is False


def test_project_passes_exact_user_connection_and_selection_to_reader():
    reader = FakeInventoryReader(inventory())
    projector = StagingSnapshotProjector(reader, FakeBinaryResolver())
    user_connection = object()

    projector.project(
        user_connection,
        export_id=EXPORT_ID,
        project_short_name="museum",
        requested_by_iri="https://example.org/users/alice",
        kind=ExportKind.STAGING_FOLDER,
        selection_iri=FOLDER,
        profile=profile(),
        generated_at=NOW,
    )

    assert reader.call == (
        user_connection,
        {
            "project_short_name": "museum",
            "kind": ExportKind.STAGING_FOLDER,
            "selection_iri": FOLDER,
            "profile": profile(),
        },
    )


def test_download_authorizer_rechecks_every_frozen_included_media() -> None:
    current_inventory = inventory()
    reader = FakeInventoryReader(current_inventory)
    projector = StagingSnapshotProjector(reader, FakeBinaryResolver())
    snapshot = projector.project_inventory(
        export_id=EXPORT_ID,
        kind=ExportKind.STAGING_FOLDER,
        selection_iri=FOLDER,
        profile=profile(),
        generated_at=NOW,
        inventory=current_inventory,
    )
    job = ExportJob(
        export_id=EXPORT_ID,
        state=ExportState.QUEUED,
        state_version=0,
        created_at=NOW,
        updated_at=NOW,
        requested_by_iri="https://example.org/users/alice",
        requested_by_user_id="alice",
        selection=snapshot.selection,
        estimated_source_bytes=snapshot.source_bytes,
        warning_count=snapshot.warning_count,
        progress=ExportProgress(
            files_total=snapshot.files_total, bytes_total=snapshot.source_bytes
        ),
        snapshot_at=NOW,
        manifest_sha256=snapshot.manifest.sha256,
    )
    connection = object()

    StagingDownloadAuthorizer(reader).authorize(
        connection, job=job, manifest=snapshot.manifest
    )
    assert reader.call[0] is connection

    missing = AuthorizedStagingInventory(
        current_inventory.area,
        current_inventory.folders,
        tuple(item for item in current_inventory.media if item.asset_id != "asset-two"),
    )
    with pytest.raises(ExportDownloadPermissionError):
        StagingDownloadAuthorizer(FakeInventoryReader(missing)).authorize(
            connection, job=job, manifest=snapshot.manifest
        )


def test_oldap_reader_uses_requester_connection_for_folder_area_and_searches(
    monkeypatch,
):
    calls = []
    connection = SimpleNamespace(context_name="DEFAULT")

    class VisibleFolder:
        name = Xsd_QName("shared:StagingFolder", validate=False)
        superclass = {}

        def get(self, key):
            return {Iri(AREA)} if str(key) == "shared:inStagingArea" else None

    class VisibleArea:
        name = Xsd_QName("shared:StagingArea", validate=False)
        superclass = {}

        def get(self, key):
            return {"Museum Staging"} if str(key) == "schema:name" else None

    class FakeFactory:
        def __init__(self, con, project):
            assert con is connection

        def read(self, iri):
            calls.append(("read", str(iri)))
            return VisibleFolder() if str(iri) == FOLDER else VisibleArea()

    class FakeResourceInstance:
        @staticmethod
        def search(**kwargs):
            assert kwargs["con"] is connection
            calls.append(("search", str(kwargs["resClass"])))
            if str(kwargs["resClass"]) == "shared:StagingFolder":
                return [
                    {
                        "iri": [FOLDER],
                        "schema:name": ["Posters"],
                        "shared:inStagingFolder": [TOP],
                    }
                ]
            return [
                {
                    "iri": ["urn:uuid:00000000-0000-4000-8000-000000000001"],
                    "shared:inStagingFolder": [FOLDER],
                    "shared:mediaAccessMode": ["local"],
                    "shared:assetId": ["asset-one"],
                    "shared:originalName": ["One.jpg"],
                    "shared:originalMimeType": ["image/jpeg"],
                    "shared:path": ["museum/source/one"],
                    "shared:checksum": ["1" * 64],
                    "schema:comment": ["Visible note"],
                }
            ]

    monkeypatch.setattr(staging_snapshot, "ResourceInstanceFactory", FakeFactory)
    monkeypatch.setattr(staging_snapshot, "ResourceInstance", FakeResourceInstance)

    result = OldapStagingInventoryReader().read(
        connection,
        project_short_name="museum",
        kind=ExportKind.STAGING_FOLDER,
        selection_iri=FOLDER,
        profile=profile(),
    )

    assert result.area == StagingAreaRecord(AREA, "Museum Staging")
    assert result.media[0].metadata == {"curatorial_note": "Visible note"}
    assert calls == [
        ("read", FOLDER),
        ("read", AREA),
        ("search", "shared:StagingFolder"),
        ("search", "shared:StagingMediaObject"),
    ]


def test_oldap_reader_rejects_unimplemented_staging_label_resolution():
    value = profile().to_dict()
    value["metadata"]["stagingMedia"][0]["valueShape"] = "iri"
    value["metadata"]["stagingMedia"][0]["resolveLabels"] = True

    with pytest.raises(ExportSnapshotError, match="label resolution"):
        OldapStagingInventoryReader().read(
            SimpleNamespace(context_name="DEFAULT"),
            project_short_name="museum",
            kind=ExportKind.STAGING_FOLDER,
            selection_iri=FOLDER,
            profile=parse_export_profile(value),
        )


def test_snapshot_rejects_portable_collisions_and_unsafe_names():
    value = inventory()
    collision = AuthorizedStagingInventory(
        value.area,
        value.folders,
        value.media + (_local_media("collision", FOLDER, "one.JPG", 5),),
    )
    resolver = FakeBinaryResolver(
        {"asset-one": 5_000, "asset-two": 7_345, "asset-collision": 100}
    )
    with pytest.raises(ExportSnapshotError, match="collide"):
        StagingSnapshotProjector(
            FakeInventoryReader(collision), resolver
        ).project_inventory(
            export_id=EXPORT_ID,
            kind=ExportKind.STAGING_FOLDER,
            selection_iri=FOLDER,
            profile=profile(),
            generated_at=NOW,
            inventory=collision,
        )

    unsafe = AuthorizedStagingInventory(
        value.area,
        value.folders + (StagingFolderRecord("urn:unsafe", "../escape", TOP),),
        value.media,
    )
    with pytest.raises(ExportSnapshotError, match="unsafe"):
        StagingSnapshotProjector(
            FakeInventoryReader(unsafe), FakeBinaryResolver()
        ).project_inventory(
            export_id=EXPORT_ID,
            kind=ExportKind.STAGING_ALL,
            selection_iri=AREA,
            profile=profile(),
            generated_at=NOW,
            inventory=unsafe,
        )


def test_snapshot_rejects_incomplete_resolver_and_total_over_limit():
    class EmptyResolver:
        def resolve(self, references):
            return {}

    with pytest.raises(ExportSnapshotError, match="incomplete inventory"):
        StagingSnapshotProjector(
            FakeInventoryReader(inventory()), EmptyResolver()
        ).project_inventory(
            export_id=EXPORT_ID,
            kind=ExportKind.STAGING_FOLDER,
            selection_iri=FOLDER,
            profile=profile(),
            generated_at=NOW,
            inventory=inventory(),
        )

    resolver = FakeBinaryResolver(
        {"asset-one": 30_000_000_000, "asset-two": 30_000_000_000}
    )
    oversized = StagingSnapshotProjector(
        FakeInventoryReader(inventory()), resolver
    ).project_inventory(
        export_id=EXPORT_ID,
        kind=ExportKind.STAGING_FOLDER,
        selection_iri=FOLDER,
        profile=profile(),
        generated_at=NOW,
        inventory=inventory(),
    )
    assert oversized.estimate_dict()["exceedsLimit"] is True

    with pytest.raises(ExportSizeLimitError):
        StagingSnapshotProjector(
            FakeInventoryReader(inventory()), resolver
        ).project_inventory(
            export_id=EXPORT_ID,
            kind=ExportKind.STAGING_FOLDER,
            selection_iri=FOLDER,
            profile=profile(),
            generated_at=NOW,
            inventory=inventory(),
            enforce_size_limit=True,
        )


def test_snapshot_uses_the_configured_environment_limit() -> None:
    projector = StagingSnapshotProjector(
        FakeInventoryReader(inventory()),
        FakeBinaryResolver(),
        max_archive_bytes=1,
    )

    estimate = projector.project_inventory(
        export_id=EXPORT_ID,
        kind=ExportKind.STAGING_FOLDER,
        selection_iri=FOLDER,
        profile=profile(),
        generated_at=NOW,
        inventory=inventory(),
    )
    assert estimate.estimate_dict()["maxArchiveBytes"] == 1
    assert estimate.estimate_dict()["exceedsLimit"] is True
    assert estimate.manifest.to_dict()["limits"] == {"maxArchiveBytes": 1}

    with pytest.raises(ExportSizeLimitError):
        projector.project_inventory(
            export_id=EXPORT_ID,
            kind=ExportKind.STAGING_FOLDER,
            selection_iri=FOLDER,
            profile=profile(),
            generated_at=NOW,
            inventory=inventory(),
            enforce_size_limit=True,
        )
