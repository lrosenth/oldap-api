"""Deterministic project-neutral archive snapshot projection tests."""

from dataclasses import replace
from datetime import UTC, datetime
import hashlib
from types import SimpleNamespace

import pytest
import rfc8785
from oldaplib.src.enums.language import Language
from oldaplib.src.xsd.xsd_string import Xsd_string

from oldap_api.exports import archive_snapshot
from oldap_api.exports.archive_snapshot import (
    ArchiveDownloadAuthorizer,
    ArchiveMediaRecord,
    ArchiveSnapshotProjector,
    ArchiveUnitRecord,
    AuthorizedArchiveInventory,
    OldapArchiveInventoryReader,
    OldapVisibleLabelResolver,
    UnavailableArchiveMediaRecord,
)
from oldap_api.exports.domain import ExportKind
from oldap_api.exports.profiles import ExportProfile, parse_export_profile
from oldap_api.exports.staging_snapshot import (
    ExportDownloadPermissionError,
    ExportSnapshotError,
    ResolvedBinarySource,
)

NOW = datetime(2026, 8, 15, 20, 0, tzinfo=UTC)
EXPORT_ID = "11111111-1111-4111-8111-111111111111"
ROOT = "urn:uuid:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
CHILD = "urn:uuid:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
OTHER = "urn:uuid:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
MEDIA = "urn:uuid:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
EXTERNAL = "urn:uuid:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
HIDDEN = "urn:uuid:ffffffff-ffff-4fff-8fff-ffffffffffff"


def profile() -> ExportProfile:
    """Return a synthetic project profile to prove generic projection."""

    return ExportProfile(
        profile_id="museum-v1",
        profile_version="1.0.0",
        project_short_name="museum",
        allowed_archive_media_classes=("museum:DigitalSurrogate",),
    )


def projected_profile() -> ExportProfile:
    """Return an archive profile with IRI label projections."""

    return parse_export_profile(
        {
            "profileId": "museum-v1",
            "profileVersion": "1.0.0",
            "projectShortName": "museum",
            "allowedArchiveMediaClasses": ["museum:DigitalSurrogate"],
            "metadata": {
                "archiveMedia": [
                    {
                        "columnName": "publication_status",
                        "propertyIri": "museum:publicationStatus",
                        "valueShape": "iri",
                        "resolveLabels": True,
                    }
                ],
                "archiveUnits": [
                    {
                        "columnName": "subjects",
                        "propertyIri": "schema:about",
                        "valueShape": "iri-list",
                        "resolveLabels": True,
                    }
                ],
                "stagingMedia": [],
            },
        }
    )


def inventory() -> AuthorizedArchiveInventory:
    """Return two roots, one shared local medium, and one external medium."""

    return AuthorizedArchiveInventory(
        units=(
            ArchiveUnitRecord(
                ROOT,
                "Posters",
                None,
                "shared:Fonds",
                media_iris=(MEDIA,),
                identifier="MUS-P",
                title={"en": "Posters", "de": "Plakate"},
                description={"en": "Poster collection"},
                creator_iris=("https://example.org/agents/curator",),
            ),
            ArchiveUnitRecord(
                CHILD,
                "Portraits",
                ROOT,
                "shared:Series",
                media_iris=(MEDIA, EXTERNAL),
                identifier="MUS-P-1",
                title={"en": "Portraits"},
                material_extent={"en": "12 items"},
            ),
            ArchiveUnitRecord(
                OTHER,
                "Audio",
                None,
                "shared:Fonds",
                title={"en": "Audio"},
            ),
        ),
        media=(
            ArchiveMediaRecord(
                MEDIA,
                (ROOT, CHILD),
                "local",
                "portrait.tif",
                "image/tiff",
                asset_id="asset-portrait",
                storage_path_candidate="museum/portrait",
                recorded_checksum="a" * 64,
                metadata={"title": {"en": "Portrait"}},
            ),
            ArchiveMediaRecord(
                EXTERNAL,
                (CHILD,),
                "external",
                "provider.jpg",
                "image/jpeg",
                external_source_url="https://provider.example/image.jpg",
            ),
        ),
    )


class Resolver:
    """Return authoritative facts for the one local test original."""

    def resolve(self, references):
        return {
            reference.media_iri: ResolvedBinarySource(
                asset_id=reference.asset_id,
                storage_path="museum/assets/asset-portrait/original/portrait.tif",
                original_name=reference.original_name,
                original_mime_type="image/tiff",
                size_bytes=12_345,
                sha256="a" * 64,
            )
            for reference in references
        }


class Reader:
    """Return one already permission-filtered test inventory."""

    def read(self, connection, **kwargs):
        del connection, kwargs
        return inventory()


def test_unit_snapshot_preserves_hierarchy_and_deduplicates_media() -> None:
    snapshot = ArchiveSnapshotProjector(Reader(), Resolver()).project_inventory(
        export_id=EXPORT_ID,
        kind=ExportKind.ARCHIVE_UNIT,
        selection_iri=ROOT,
        profile=profile(),
        generated_at=NOW,
        inventory=inventory(),
        requested_by_iri="https://example.org/users/alice",
    )

    value = snapshot.manifest.to_dict()
    assert snapshot.files_total == 1
    assert snapshot.source_bytes == 12_345
    assert snapshot.warning_count == 1
    assert [item["relativePath"] for item in value["directories"]] == [
        "Posters",
        "Posters/Portraits",
    ]
    assert len(value["media"]) == 2
    local = next(item for item in value["media"] if item["included"])
    assert local["relativePath"] == "Posters/portrait.tif"
    assert local["metadata"]["archive_unit_iris"] == [ROOT, CHILD]
    assert local["metadata"]["archive_unit_paths"] == [
        "Posters",
        "Posters/Portraits",
    ]
    assert value["archiveUnits"][1]["parentUnitIri"] == ROOT
    assert value["archiveUnits"][1]["materialExtent"] == {"en": "12 items"}


def test_all_snapshot_wraps_visible_roots_and_omits_no_units() -> None:
    snapshot = ArchiveSnapshotProjector(Reader(), Resolver()).project_inventory(
        export_id=EXPORT_ID,
        kind=ExportKind.ARCHIVE_ALL,
        selection_iri=None,
        profile=profile(),
        generated_at=NOW,
        inventory=inventory(),
    )

    value = snapshot.manifest.to_dict()
    assert snapshot.selection.selection_iri is None
    assert {item["relativePath"] for item in value["directories"]} == {
        "Archive/Audio",
        "Archive/Posters",
        "Archive/Posters/Portraits",
    }
    assert len(value["archiveUnits"]) == 3


def test_unit_snapshot_ignores_unsafe_names_outside_selected_subtree() -> None:
    """Unrelated visible roots must not block a safe ArchiveUnit export."""

    value = inventory()
    unsafe_other = replace(value.units[2], name="Not/a portable root")
    scoped = replace(value, units=(*value.units[:2], unsafe_other))

    snapshot = ArchiveSnapshotProjector(Reader(), Resolver()).project_inventory(
        export_id=EXPORT_ID,
        kind=ExportKind.ARCHIVE_UNIT,
        selection_iri=ROOT,
        profile=profile(),
        generated_at=NOW,
        inventory=scoped,
    )

    assert {
        item["unitIri"] for item in snapshot.manifest.to_dict()["archiveUnits"]
    } == {
        ROOT,
        CHILD,
    }
    with pytest.raises(ExportSnapshotError, match="Not/a portable root"):
        ArchiveSnapshotProjector(Reader(), Resolver()).project_inventory(
            export_id=EXPORT_ID,
            kind=ExportKind.ARCHIVE_ALL,
            selection_iri=None,
            profile=profile(),
            generated_at=NOW,
            inventory=scoped,
        )


def test_cycle_and_portable_sibling_collision_fail_closed() -> None:
    cyclic = AuthorizedArchiveInventory(
        units=(
            ArchiveUnitRecord(ROOT, "One", CHILD, "shared:Fonds"),
            ArchiveUnitRecord(CHILD, "Two", ROOT, "shared:Series"),
        ),
        media=(),
    )
    with pytest.raises(ExportSnapshotError, match="cycle"):
        ArchiveSnapshotProjector(Reader(), Resolver()).project_inventory(
            export_id=EXPORT_ID,
            kind=ExportKind.ARCHIVE_UNIT,
            selection_iri=ROOT,
            profile=profile(),
            generated_at=NOW,
            inventory=cyclic,
        )

    collision = AuthorizedArchiveInventory(
        units=(
            ArchiveUnitRecord(ROOT, "Root", None, "shared:Fonds"),
            ArchiveUnitRecord(CHILD, "Series", ROOT, "shared:Series"),
            ArchiveUnitRecord(OTHER, "series", ROOT, "shared:Series"),
        ),
        media=(),
    )
    with pytest.raises(ExportSnapshotError, match="collide"):
        ArchiveSnapshotProjector(Reader(), Resolver()).project_inventory(
            export_id=EXPORT_ID,
            kind=ExportKind.ARCHIVE_UNIT,
            selection_iri=ROOT,
            profile=profile(),
            generated_at=NOW,
            inventory=collision,
        )


def test_unreadable_link_becomes_opaque_warning_without_binary() -> None:
    value = inventory()
    hidden = AuthorizedArchiveInventory(
        value.units,
        value.media,
        (UnavailableArchiveMediaRecord(HIDDEN, (CHILD,)),),
    )
    snapshot = ArchiveSnapshotProjector(Reader(), Resolver()).project_inventory(
        export_id=EXPORT_ID,
        kind=ExportKind.ARCHIVE_UNIT,
        selection_iri=ROOT,
        profile=profile(),
        generated_at=NOW,
        inventory=hidden,
    )

    excluded = [
        item for item in snapshot.manifest.to_dict()["media"] if not item["included"]
    ]
    assert snapshot.warning_count == 2
    hidden_row = next(item for item in excluded if item["mediaIri"] == HIDDEN)
    assert hidden_row["exclusionReason"] == "ORIGINAL_NOT_EXPORTABLE"
    assert hidden_row["relativePath"].startswith("Posters/Portraits/unavailable-media-")
    assert "binarySource" not in hidden_row


def test_oldap_reader_uses_requester_connection_and_resolves_profile_labels(
    monkeypatch,
) -> None:
    connection = SimpleNamespace(context_name="DEFAULT")
    status = "urn:uuid:11111111-2222-4333-8444-555555555555"
    subject = "urn:uuid:66666666-7777-4888-8999-000000000000"
    calls = []

    class Labels:
        def resolve(self, actual_connection, **kwargs):
            assert actual_connection is connection
            assert kwargs["iris"] == {status, subject}
            return {status: "Published", subject: "Posters"}

    class Search:
        @staticmethod
        def search(**kwargs):
            assert kwargs["con"] is connection
            calls.append(str(kwargs["resClass"]))
            if str(kwargs["resClass"]) == "shared:ArchiveUnit":
                return [
                    {
                        "iri": [ROOT],
                        "schema:name": [Xsd_string("Posters", lang=Language.EN)],
                        "shared:archiveLevel": ["shared:Fonds"],
                        "shared:hasMediaObject": [MEDIA, HIDDEN],
                        "schema:about": [subject],
                    }
                ]
            return [
                {
                    "iri": [MEDIA],
                    "shared:mediaAccessMode": ["local"],
                    "shared:assetId": ["asset-portrait"],
                    "shared:originalName": ["portrait.tif"],
                    "shared:originalMimeType": ["image/tiff"],
                    "shared:path": ["museum/portrait"],
                    "shared:checksum": ["a" * 64],
                    "museum:publicationStatus": [status],
                }
            ]

    monkeypatch.setattr(archive_snapshot, "ResourceInstance", Search)
    result = OldapArchiveInventoryReader(Labels()).read(
        connection,
        project_short_name="museum",
        profile=projected_profile(),
    )

    assert calls == ["shared:ArchiveUnit", "museum:DigitalSurrogate"]
    assert result.units[0].metadata == {"subjects": {subject: "Posters"}}
    assert result.units[0].name == "Posters"
    assert result.units[0].title == {"en": "Posters"}
    assert result.media[0].metadata == {"publication_status": {status: "Published"}}
    assert result.media[0].unit_iris == (ROOT,)
    assert result.unavailable_media == (UnavailableArchiveMediaRecord(HIDDEN, (ROOT,)),)


def test_visible_label_resolver_reads_through_requester_connection(monkeypatch) -> None:
    connection = object()
    target = "urn:uuid:12121212-3434-4567-8787-909090909090"

    class Visible:
        def get(self, key):
            return {"Readable label"} if str(key) == "skos:prefLabel" else None

    class Factory:
        def __init__(self, con, project):
            assert con is connection
            assert str(project) == "museum"

        def read(self, iri):
            assert str(iri) == target
            return Visible()

    monkeypatch.setattr(archive_snapshot, "ResourceInstanceFactory", Factory)

    assert OldapVisibleLabelResolver().resolve(
        connection,
        project_short_name="museum",
        iris={target},
    ) == {target: "Readable label"}


def test_archive_download_rechecks_profile_units_media_and_relationships() -> None:
    current = inventory()

    class StaticReader:
        def __init__(self, value):
            self.value = value

        def read(self, connection, **kwargs):
            del connection, kwargs
            return self.value

    class Registry:
        def __init__(self, value):
            self.value = value

        def get_active(self, project_short_name):
            assert project_short_name == "museum"
            return self.value

    snapshot = ArchiveSnapshotProjector(Reader(), Resolver()).project_inventory(
        export_id=EXPORT_ID,
        kind=ExportKind.ARCHIVE_UNIT,
        selection_iri=ROOT,
        profile=profile(),
        generated_at=NOW,
        inventory=current,
    )
    job = SimpleNamespace(selection=snapshot.selection)
    authorizer = ArchiveDownloadAuthorizer(StaticReader(current), Registry(profile()))

    authorizer.authorize(object(), job=job, manifest=snapshot.manifest)

    moved_child = AuthorizedArchiveInventory(
        tuple(
            replace(unit, parent_iri=OTHER) if unit.iri == CHILD else unit
            for unit in current.units
        ),
        current.media,
    )
    with pytest.raises(ExportDownloadPermissionError):
        ArchiveDownloadAuthorizer(
            StaticReader(moved_child), Registry(profile())
        ).authorize(object(), job=job, manifest=snapshot.manifest)

    changed_relation = AuthorizedArchiveInventory(
        current.units,
        tuple(
            replace(media, unit_iris=(ROOT,)) if media.iri == MEDIA else media
            for media in current.media
        ),
    )
    with pytest.raises(ExportDownloadPermissionError):
        ArchiveDownloadAuthorizer(
            StaticReader(changed_relation), Registry(profile())
        ).authorize(object(), job=job, manifest=snapshot.manifest)

    changed_profile = profile()
    changed_profile = ExportProfile(
        changed_profile.profile_id,
        "1.0.1",
        changed_profile.project_short_name,
        changed_profile.allowed_archive_media_classes,
    )
    assert hashlib.sha256(rfc8785.dumps(changed_profile.to_dict())).hexdigest() != (
        snapshot.selection.profile_sha256
    )
    with pytest.raises(ExportDownloadPermissionError, match="profile"):
        ArchiveDownloadAuthorizer(
            StaticReader(current), Registry(changed_profile)
        ).authorize(object(), job=job, manifest=snapshot.manifest)
