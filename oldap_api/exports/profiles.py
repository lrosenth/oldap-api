"""Validation boundary for declarative project ZIP-export profiles.

Profiles may describe additional metadata projection only. They cannot replace
the shared selection, authorization, path, lifecycle, checksum, or binary
access rules owned by the generic export service.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

PROJECT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
PROFILE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}-v[1-9][0-9]*$")
VERSION_RE = re.compile(r"^[1-9][0-9]*\.[0-9]+\.[0-9]+$")
COLUMN_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
QNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*:[A-Za-z_][A-Za-z0-9_.-]*$")

COMMON_METADATA_COLUMNS = frozenset(
    {
        "relative_path",
        "included",
        "exclusion_reason",
        "media_iri",
        "asset_id",
        "original_filename",
        "original_mime_type",
        "size_bytes",
        "sha256",
        "recorded_checksum",
        "container_iri",
        "container_path",
        "source_modified_at",
    }
)

ALLOWED_VALUE_SHAPES = frozenset(
    {"scalar", "lang-map", "iri", "iri-list", "value-list"}
)

RESERVED_SOURCE_PROPERTIES = frozenset(
    {
        "shared:assetId",
        "shared:checksum",
        "shared:derivativeName",
        "shared:imageId",
        "shared:mediaAccessMode",
        "shared:mediaUrl",
        "shared:originalMimeType",
        "shared:originalName",
        "shared:path",
        "shared:protocol",
        "shared:serverUrl",
        "shared:thumbnailUrl",
    }
)


class ExportProfileError(ValueError):
    """Raised when a server-owned project profile is unsafe or ambiguous."""


class ExportProfileNotFoundError(LookupError):
    """Raised when no active server-owned profile exists for a project."""


@dataclass(frozen=True, slots=True)
class ExportMetadataProjection:
    """One declarative OLDAP property-to-CSV projection."""

    column_name: str
    property_iri: str
    value_shape: str
    resolve_labels: bool = False

    def to_dict(self) -> dict[str, object]:
        """Return the canonical JSON representation used in profile digests."""

        return {
            "columnName": self.column_name,
            "propertyIri": self.property_iri,
            "valueShape": self.value_shape,
            "resolveLabels": self.resolve_labels,
        }


@dataclass(frozen=True, slots=True)
class ExportProfile:
    """Validated project-owned additions to the generic export contract."""

    profile_id: str
    profile_version: str
    project_short_name: str
    allowed_archive_media_classes: tuple[str, ...]
    archive_media: tuple[ExportMetadataProjection, ...] = ()
    archive_units: tuple[ExportMetadataProjection, ...] = ()
    staging_media: tuple[ExportMetadataProjection, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return one stable camel-case representation for manifests and tests."""

        return {
            "profileId": self.profile_id,
            "profileVersion": self.profile_version,
            "projectShortName": self.project_short_name,
            "allowedArchiveMediaClasses": list(self.allowed_archive_media_classes),
            "metadata": {
                "archiveMedia": [item.to_dict() for item in self.archive_media],
                "archiveUnits": [item.to_dict() for item in self.archive_units],
                "stagingMedia": [item.to_dict() for item in self.staging_media],
            },
        }


class FileExportProfileRegistry:
    """Load active project profiles from a trusted server-side directory.

    A deployment may mount its own directory through
    ``OLDAP_EXPORT_PROFILE_DIR``. The package-bundled directory provides the
    initial Fasnacht profile and keeps the runtime independent from repository
    documentation paths.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    @classmethod
    def from_environment(cls) -> "FileExportProfileRegistry":
        """Build the registry from deployment configuration or package data."""

        configured = os.getenv("OLDAP_EXPORT_PROFILE_DIR", "").strip()
        root = (
            Path(configured) if configured else Path(__file__).parent / "profile_data"
        )
        return cls(root)

    def get_active(self, project_short_name: str) -> ExportProfile:
        """Return the validated active profile for one exact project name."""

        if PROJECT_RE.fullmatch(project_short_name) is None:
            raise ExportProfileNotFoundError("Export profile not found.")
        path = self._root / f"{project_short_name}.json"
        try:
            if (
                path.is_symlink()
                or not path.is_file()
                or path.stat().st_size > 1_000_000
            ):
                raise ExportProfileNotFoundError("Export profile not found.")
            value = json.loads(path.read_text(encoding="utf-8"))
        except ExportProfileNotFoundError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ExportProfileError(
                "Export profile configuration is invalid."
            ) from error
        profile = parse_export_profile(value)
        if profile.project_short_name != project_short_name:
            raise ExportProfileError("Export profile project identity is inconsistent.")
        return profile


def parse_export_profile(value: Mapping[str, Any]) -> ExportProfile:
    """Validate a closed server-side project export profile.

    Args:
        value: JSON-compatible mapping loaded from trusted project
            configuration.

    Returns:
        Immutable profile safe for snapshot construction.

    Raises:
        ExportProfileError: If required fields, identifiers, classes, columns,
            or value shapes violate the generic boundary.
    """

    if not isinstance(value, Mapping):
        raise ExportProfileError("Export profile must be an object.")
    allowed_keys = {
        "profileId",
        "profileVersion",
        "projectShortName",
        "allowedArchiveMediaClasses",
        "metadata",
    }
    _reject_extra_keys(value, allowed_keys, "profile")

    profile_id = _required_string(value, "profileId")
    version = _required_string(value, "profileVersion")
    project = _required_string(value, "projectShortName")
    if not PROFILE_ID_RE.fullmatch(profile_id):
        raise ExportProfileError("profileId must end in a positive -vN version.")
    if not VERSION_RE.fullmatch(version):
        raise ExportProfileError("profileVersion must be semantic MAJOR.MINOR.PATCH.")
    if not PROJECT_RE.fullmatch(project):
        raise ExportProfileError("projectShortName is invalid.")
    major = version.split(".", maxsplit=1)[0]
    if profile_id != f"{project.lower()}-v{major}":
        raise ExportProfileError(
            "profileId must combine the lower-case projectShortName and profile major version."
        )

    raw_classes = value.get("allowedArchiveMediaClasses")
    if not isinstance(raw_classes, list) or not raw_classes:
        raise ExportProfileError("allowedArchiveMediaClasses must be non-empty.")
    classes = tuple(
        _resource_identifier(item, "archive media class") for item in raw_classes
    )
    if len(classes) != len(set(classes)):
        raise ExportProfileError("allowedArchiveMediaClasses contains duplicates.")

    metadata = value.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise ExportProfileError("metadata must be an object.")
    _reject_extra_keys(
        metadata,
        {"archiveMedia", "archiveUnits", "stagingMedia"},
        "metadata",
    )
    projections = {
        name: _parse_projections(metadata.get(name, []), name)
        for name in ("archiveMedia", "archiveUnits", "stagingMedia")
    }
    all_columns = [item.column_name for items in projections.values() for item in items]
    if len(all_columns) != len(set(all_columns)):
        raise ExportProfileError("Metadata column names must be globally unique.")

    return ExportProfile(
        profile_id=profile_id,
        profile_version=version,
        project_short_name=project,
        allowed_archive_media_classes=classes,
        archive_media=projections["archiveMedia"],
        archive_units=projections["archiveUnits"],
        staging_media=projections["stagingMedia"],
    )


def _parse_projections(
    value: Any, section: str
) -> tuple[ExportMetadataProjection, ...]:
    if not isinstance(value, list):
        raise ExportProfileError(f"metadata.{section} must be an array.")
    result: list[ExportMetadataProjection] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise ExportProfileError(f"metadata.{section}[{index}] must be an object.")
        _reject_extra_keys(
            raw,
            {"columnName", "propertyIri", "valueShape", "resolveLabels"},
            f"metadata.{section}[{index}]",
        )
        column = _required_string(raw, "columnName")
        if not COLUMN_RE.fullmatch(column) or column in COMMON_METADATA_COLUMNS:
            raise ExportProfileError(f"Unsafe or reserved metadata column: {column}.")
        property_iri = _resource_identifier(
            _required_string(raw, "propertyIri"), "metadata property"
        )
        if property_iri in RESERVED_SOURCE_PROPERTIES:
            raise ExportProfileError(
                f"Security-sensitive metadata property is reserved: {property_iri}."
            )
        shape = _required_string(raw, "valueShape")
        if shape not in ALLOWED_VALUE_SHAPES:
            raise ExportProfileError(f"Unsupported metadata valueShape: {shape}.")
        resolve_labels = raw.get("resolveLabels", False)
        if not isinstance(resolve_labels, bool):
            raise ExportProfileError("resolveLabels must be boolean.")
        if resolve_labels and shape not in {"iri", "iri-list"}:
            raise ExportProfileError(
                "resolveLabels is allowed only for iri and iri-list projections."
            )
        result.append(
            ExportMetadataProjection(column, property_iri, shape, resolve_labels)
        )
    return tuple(result)


def _resource_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ExportProfileError(f"Invalid {label}.")
    if QNAME_RE.fullmatch(value):
        return value
    parsed = urlsplit(value)
    if (
        parsed.scheme in {"http", "https"}
        and parsed.netloc
        and (parsed.path or parsed.fragment)
    ):
        return value
    raise ExportProfileError(f"Invalid {label}: expected QName or HTTP(S) IRI.")


def _required_string(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ExportProfileError(f"{key} must be a non-empty string.")
    return result


def _reject_extra_keys(value: Mapping[str, Any], allowed: set[str], label: str) -> None:
    extras = sorted(set(value) - allowed)
    if extras:
        raise ExportProfileError(f"Unknown {label} fields: {', '.join(extras)}.")
