"""Immutable canonical worker manifests for project-neutral ZIP exports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping
from uuid import UUID

import rfc8785

from .domain import MAX_EXPORT_BYTES, ExportJob, ExportKind, ExportState

MANIFEST_DOCUMENT_TYPE = "oldap.zip-export.manifest"
MANIFEST_SCHEMA_VERSION = "1.0.0"
MAX_MANIFEST_ENTRIES = 1_000_000


class ExportManifestError(ValueError):
    """Raised when a worker manifest is malformed or mismatched to its job."""


@dataclass(frozen=True, slots=True)
class ExportManifest:
    """RFC-8785-canonical immutable export snapshot passed to the worker."""

    export_id: str
    generated_at: datetime
    kind: ExportKind
    project_short_name: str
    canonical_json: bytes
    sha256: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExportManifest":
        """Validate the closed envelope and create canonical immutable bytes."""

        if not isinstance(value, Mapping):
            raise ExportManifestError("Export manifest must be an object.")
        required = {
            "documentType",
            "schemaVersion",
            "exportId",
            "generatedAt",
            "kind",
            "projectShortName",
            "requestedByIri",
            "profile",
            "selection",
            "limits",
            "directories",
            "media",
        }
        allowed = required | {"archiveUnits"}
        if not required <= set(value) <= allowed:
            raise ExportManifestError(
                "Export manifest fields must match the closed v1 envelope."
            )
        if value["documentType"] != MANIFEST_DOCUMENT_TYPE:
            raise ExportManifestError("Unsupported export manifest documentType.")
        if value["schemaVersion"] != MANIFEST_SCHEMA_VERSION:
            raise ExportManifestError("Unsupported export manifest schemaVersion.")
        export_id = _canonical_uuid(value["exportId"], "exportId")
        generated_at = _timestamp(value["generatedAt"], "generatedAt")
        try:
            kind = ExportKind(value["kind"])
        except (TypeError, ValueError) as error:
            raise ExportManifestError("Unsupported export kind.") from error
        project = value["projectShortName"]
        if not isinstance(project, str) or not project:
            raise ExportManifestError("projectShortName must be a non-empty string.")
        limits = value["limits"]
        if (
            not isinstance(limits, Mapping)
            or set(limits) != {"maxArchiveBytes"}
            or isinstance(limits["maxArchiveBytes"], bool)
            or not isinstance(limits["maxArchiveBytes"], int)
            or not 1 <= limits["maxArchiveBytes"] <= MAX_EXPORT_BYTES
        ):
            raise ExportManifestError("Manifest limits exceed the export v1 ceiling.")
        directories = value["directories"]
        media = value["media"]
        if not isinstance(directories, list) or len(directories) > MAX_MANIFEST_ENTRIES:
            raise ExportManifestError("Manifest directories exceed the v1 bound.")
        if not isinstance(media, list) or len(media) > MAX_MANIFEST_ENTRIES:
            raise ExportManifestError("Manifest media exceed the v1 bound.")
        archive_units = value.get("archiveUnits", [])
        if (
            not isinstance(archive_units, list)
            or len(archive_units) > MAX_MANIFEST_ENTRIES
        ):
            raise ExportManifestError("Manifest archive units exceed the v1 bound.")
        if kind in {ExportKind.ARCHIVE_UNIT, ExportKind.ARCHIVE_ALL}:
            if "archiveUnits" not in value:
                raise ExportManifestError(
                    "Archive manifests must contain archiveUnits."
                )
        elif "archiveUnits" in value:
            raise ExportManifestError(
                "Staging manifests must not contain archiveUnits."
            )
        _validate_media_inventory(media)
        _validate_archive_units(archive_units)
        if kind in {ExportKind.ARCHIVE_UNIT, ExportKind.ARCHIVE_ALL}:
            _validate_archive_inventory(directories, media, archive_units)
        try:
            canonical = rfc8785.dumps(dict(value))
        except (rfc8785.CanonicalizationError, TypeError) as error:
            raise ExportManifestError(
                "Manifest is not RFC-8785 serializable."
            ) from error
        return cls(
            export_id=export_id,
            generated_at=generated_at,
            kind=kind,
            project_short_name=project,
            canonical_json=canonical,
            sha256=hashlib.sha256(canonical).hexdigest(),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a fresh JSON-compatible representation of the snapshot."""

        return json.loads(self.canonical_json)

    def validate_for_job(self, job: ExportJob) -> None:
        """Bind immutable manifest identity, profile, selection, and totals."""

        self.validate_identity_for_job(job)
        value = self.to_dict()
        included_media = [item for item in value["media"] if item["included"]]
        excluded_media = [item for item in value["media"] if not item["included"]]
        expected_sizes = [
            item["binarySource"]["expectedSizeBytes"] for item in included_media
        ]
        if (
            job.state is not ExportState.QUEUED
            or len(included_media) != job.progress.files_total
            or len(excluded_media) != job.warning_count
            or sum(expected_sizes) != job.estimated_source_bytes
            or job.progress.bytes_total != job.estimated_source_bytes
        ):
            raise ExportManifestError(
                "Manifest does not match its immutable export job."
            )

    def validate_identity_for_job(self, job: ExportJob) -> None:
        """Verify immutable binding independently of the current lifecycle state."""

        value = self.to_dict()
        profile = value["profile"]
        selection = value["selection"]
        if (
            job.snapshot_at is None
            or self.export_id != job.export_id
            or self.generated_at != job.snapshot_at
            or self.kind is not job.selection.kind
            or self.project_short_name != job.selection.project_short_name
            or value["requestedByIri"] != job.requested_by_iri
            or profile
            != {
                "profileId": job.selection.profile_id,
                "profileVersion": job.selection.profile_version,
                "profileSha256": job.selection.profile_sha256,
                "metadataSchemaVersion": job.selection.metadata_schema_version,
            }
            or selection.get("iri") != job.selection.selection_iri
            or selection.get("displayName") != job.selection.display_name
            or selection.get("displayPath") != job.selection.display_path
            or self.sha256 != job.manifest_sha256
        ):
            raise ExportManifestError(
                "Manifest identity does not match its immutable export job."
            )


def _validate_media_inventory(media: list[Any]) -> None:
    indexes: set[int] = set()
    paths: set[str] = set()
    for item in media:
        if not isinstance(item, Mapping):
            raise ExportManifestError("Manifest media entries must be objects.")
        included = item.get("included")
        index = item.get("entryIndex")
        path = item.get("relativePath")
        if not isinstance(included, bool):
            raise ExportManifestError("Manifest included flags must be boolean.")
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ExportManifestError("Manifest entryIndex must be non-negative.")
        if index in indexes:
            raise ExportManifestError("Manifest entryIndex values must be unique.")
        if not isinstance(path, str) or not path or path in paths:
            raise ExportManifestError("Manifest media relative paths must be unique.")
        indexes.add(index)
        paths.add(path)
        binary = item.get("binarySource")
        exclusion = item.get("exclusionReason")
        if included:
            if not isinstance(binary, Mapping) or exclusion is not None:
                raise ExportManifestError(
                    "Included media require binarySource and no exclusionReason."
                )
            size = binary.get("expectedSizeBytes")
            if (
                isinstance(size, bool)
                or not isinstance(size, int)
                or not 0 <= size <= MAX_EXPORT_BYTES
            ):
                raise ExportManifestError(
                    "Included media require a bounded expectedSizeBytes value."
                )
        elif binary is not None or not isinstance(exclusion, str):
            raise ExportManifestError(
                "Excluded media require exclusionReason and no binarySource."
            )


def _validate_archive_units(units: list[Any]) -> None:
    """Validate the closed common archive-unit metadata projection."""

    required = {
        "relativePath",
        "unitIri",
        "archiveLevelIri",
        "title",
        "identifier",
        "description",
        "temporal",
        "materialExtent",
        "creatorIris",
        "provenance",
        "conditionsOfAccess",
        "metadata",
    }
    iris: set[str] = set()
    paths: set[str] = set()
    for unit in units:
        if not isinstance(unit, Mapping) or not required <= set(unit) <= required | {
            "parentUnitIri"
        }:
            raise ExportManifestError("Manifest archive units must be closed objects.")
        iri = unit["unitIri"]
        path = unit["relativePath"]
        creators = unit["creatorIris"]
        metadata = unit["metadata"]
        if (
            not isinstance(iri, str)
            or not iri
            or iri in iris
            or not isinstance(path, str)
            or not path
            or path in paths
            or not isinstance(unit["archiveLevelIri"], str)
            or not unit["archiveLevelIri"]
            or not isinstance(unit["identifier"], str)
            or not isinstance(unit["temporal"], str)
            or not isinstance(creators, list)
            or len(creators) > 10_000
            or not all(isinstance(item, str) for item in creators)
            or not isinstance(metadata, Mapping)
            or len(metadata) > 256
        ):
            raise ExportManifestError("Manifest archive-unit facts are invalid.")
        parent = unit.get("parentUnitIri")
        if parent is not None and (not isinstance(parent, str) or not parent):
            raise ExportManifestError("Manifest archive-unit parent is invalid.")
        for value in (
            unit["title"],
            unit["description"],
            unit["materialExtent"],
            unit["provenance"],
            unit["conditionsOfAccess"],
        ):
            if not _valid_metadata_value(value):
                raise ExportManifestError("Manifest archive-unit metadata is invalid.")
        if any(
            not isinstance(key, str) or not _valid_metadata_value(value)
            for key, value in metadata.items()
        ):
            raise ExportManifestError("Manifest archive-unit metadata is invalid.")
        iris.add(iri)
        paths.add(path)
    if any(
        unit.get("parentUnitIri") not in iris
        for unit in units
        if unit.get("parentUnitIri")
    ):
        raise ExportManifestError(
            "Manifest archive-unit parent is outside the snapshot."
        )


def _validate_archive_inventory(
    directories: list[Any], media: list[Any], units: list[Any]
) -> None:
    """Bind archive metadata rows, directories, and media containers exactly."""

    if any(
        not isinstance(directory, Mapping)
        or set(directory) != {"relativePath", "containerIri"}
        or not isinstance(directory["relativePath"], str)
        or not isinstance(directory["containerIri"], str)
        for directory in directories
    ):
        raise ExportManifestError("Manifest archive directories are invalid.")
    directory_pairs = {
        (directory["containerIri"], directory["relativePath"])
        for directory in directories
    }
    unit_pairs = {(unit["unitIri"], unit["relativePath"]) for unit in units}
    if len(directory_pairs) != len(directories) or directory_pairs != unit_pairs:
        raise ExportManifestError(
            "Manifest archive units differ from directory inventory."
        )
    unit_iris = {unit["unitIri"] for unit in units}
    if any(item.get("containerIri") not in unit_iris for item in media):
        raise ExportManifestError(
            "Manifest media container is outside the archive snapshot."
        )


def _valid_metadata_value(value: Any) -> bool:
    if isinstance(value, (str, bool, int, float)):
        return not isinstance(value, str) or len(value) <= 1_000_000
    if isinstance(value, list):
        return len(value) <= 10_000 and all(
            isinstance(item, str) and len(item) <= 10_000 for item in value
        )
    if isinstance(value, Mapping):
        return len(value) <= 256 and all(
            isinstance(key, str) and isinstance(item, str) and len(item) <= 100_000
            for key, item in value.items()
        )
    return False


def _canonical_uuid(value: Any, field: str) -> str:
    try:
        canonical = str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise ExportManifestError(f"{field} must be a canonical UUID.") from error
    if value != canonical:
        raise ExportManifestError(f"{field} must be a canonical UUID.")
    return canonical


def _timestamp(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise ExportManifestError(f"{field} must be an RFC 3339 timestamp.") from error
    if parsed.tzinfo is None:
        raise ExportManifestError(f"{field} must include a timezone.")
    return parsed.astimezone(UTC)
