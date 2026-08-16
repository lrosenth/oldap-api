"""Canonical manifest and immutable job-binding tests for ZIP export v1."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from oldap_api.exports.domain import (
    MAX_EXPORT_BYTES,
    ExportJob,
    ExportKind,
    ExportProgress,
    ExportSelectionSnapshot,
    ExportState,
)
from oldap_api.exports.manifest import ExportManifest, ExportManifestError

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
PROFILE_SHA = "a" * 64
MANIFEST_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "doc"
    / "zip-export"
    / "v1"
    / "manifest.schema.json"
)


def manifest_value() -> dict:
    """Return one closed worker manifest with two local originals."""

    return {
        "documentType": "oldap.zip-export.manifest",
        "schemaVersion": "1.0.0",
        "exportId": "11111111-1111-4111-8111-111111111111",
        "generatedAt": "2026-08-14T12:00:00Z",
        "kind": "ARCHIVE_UNIT",
        "projectShortName": "museum",
        "requestedByIri": "https://example.org/users/alice",
        "profile": {
            "profileId": "museum-v1",
            "profileVersion": "1.0.0",
            "profileSha256": PROFILE_SHA,
            "metadataSchemaVersion": "1.0.0",
        },
        "selection": {
            "iri": "urn:uuid:22222222-2222-4222-8222-222222222222",
            "displayName": "Posters",
            "displayPath": "Collection/Posters",
        },
        "limits": {"maxArchiveBytes": MAX_EXPORT_BYTES},
        "directories": [
            {
                "relativePath": "Posters",
                "containerIri": "urn:uuid:22222222-2222-4222-8222-222222222222",
            }
        ],
        "archiveUnits": [
            {
                "relativePath": "Posters",
                "unitIri": "urn:uuid:22222222-2222-4222-8222-222222222222",
                "archiveLevelIri": "shared:Fonds",
                "title": {"en": "Posters"},
                "identifier": "MUS-P",
                "description": {},
                "temporal": "",
                "materialExtent": {},
                "creatorIris": [],
                "provenance": {},
                "conditionsOfAccess": {},
                "metadata": {},
            }
        ],
        "media": [
            {
                "entryIndex": 0,
                "relativePath": "Posters/one.jpg",
                "mediaIri": "urn:uuid:33333333-3333-4333-8333-333333333333",
                "containerIri": "urn:uuid:22222222-2222-4222-8222-222222222222",
                "included": True,
                "binarySource": {
                    "assetId": "asset-one",
                    "storagePath": "originals/one.jpg",
                    "originalName": "one.jpg",
                    "originalMimeType": "image/jpeg",
                    "expectedSizeBytes": 5_000,
                },
                "metadata": {"rating": 2.5},
            },
            {
                "entryIndex": 1,
                "relativePath": "Posters/two.jpg",
                "mediaIri": "urn:uuid:44444444-4444-4444-8444-444444444444",
                "containerIri": "urn:uuid:22222222-2222-4222-8222-222222222222",
                "included": True,
                "binarySource": {
                    "assetId": "asset-two",
                    "storagePath": "originals/two.jpg",
                    "originalName": "two.jpg",
                    "originalMimeType": "image/jpeg",
                    "expectedSizeBytes": 7_345,
                },
                "metadata": {},
            },
        ],
    }


def bound_job() -> tuple[ExportJob, ExportManifest]:
    """Return a QUEUED job exactly bound to the canonical test manifest."""

    manifest = ExportManifest.from_dict(manifest_value())
    job = ExportJob(
        export_id=manifest.export_id,
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
            profile_sha256=PROFILE_SHA,
        ),
        estimated_source_bytes=12_345,
        progress=ExportProgress(files_total=2, bytes_total=12_345),
        snapshot_at=NOW,
        manifest_sha256=manifest.sha256,
    )
    return job, manifest


def test_manifest_digest_is_rfc8785_canonical_and_order_independent():
    value = manifest_value()
    reordered = {key: value[key] for key in reversed(value)}

    first = ExportManifest.from_dict(value)
    second = ExportManifest.from_dict(reordered)

    assert first.canonical_json == second.canonical_json
    assert first.sha256 == second.sha256
    assert first.to_dict() == value


def test_archive_manifest_matches_schema_and_archive_units_are_kind_bound():
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    value = manifest_value()

    validator.validate(value)

    missing_units = deepcopy(value)
    del missing_units["archiveUnits"]
    assert any(
        error.validator == "required" for error in validator.iter_errors(missing_units)
    )
    staging_with_units = deepcopy(value)
    staging_with_units["kind"] = "STAGING_FOLDER"
    assert any(
        error.validator == "not" for error in validator.iter_errors(staging_with_units)
    )


def test_manifest_binds_profile_selection_inventory_and_size_to_job():
    job, manifest = bound_job()

    manifest.validate_for_job(job)

    with pytest.raises(ExportManifestError, match="does not match"):
        manifest.validate_for_job(replace(job, estimated_source_bytes=12_344))


def test_manifest_rejects_duplicate_paths_and_missing_expected_size():
    duplicate = manifest_value()
    duplicate["media"][1]["relativePath"] = duplicate["media"][0]["relativePath"]
    with pytest.raises(ExportManifestError, match="relative paths must be unique"):
        ExportManifest.from_dict(duplicate)

    missing_size = deepcopy(manifest_value())
    del missing_size["media"][0]["binarySource"]["expectedSizeBytes"]
    with pytest.raises(ExportManifestError, match="expectedSizeBytes"):
        ExportManifest.from_dict(missing_size)


def test_manifest_rejects_noncanonical_uuid_and_unknown_envelope_field():
    value = manifest_value()
    value["exportId"] = "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
    with pytest.raises(ExportManifestError, match="canonical UUID"):
        ExportManifest.from_dict(value)

    value = manifest_value() | {"workerCallback": "https://attacker.example"}
    with pytest.raises(ExportManifestError, match="closed v1 envelope"):
        ExportManifest.from_dict(value)
