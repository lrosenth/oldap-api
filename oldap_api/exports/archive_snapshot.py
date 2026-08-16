"""Project authorized archive inventories into immutable export manifests.

The projector is deliberately independent from Fasnacht classes. A later OLDAP
reader supplies only requester-visible ``shared:ArchiveUnit`` records and media
belonging to classes permitted by the active server-owned export profile.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, Protocol

import rfc8785
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission, OldapErrorNotFound
from oldaplib.src.objectfactory import ResourceInstance, ResourceInstanceFactory
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.floatingpoint import FloatingPoint
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from .domain import MAX_EXPORT_BYTES, ExportKind, ExportSelectionSnapshot
from .manifest import ExportManifest
from .profiles import ExportMetadataProjection, ExportProfile
from .snapshot_common import (
    BinarySourceResolver,
    ExportSizeLimitError,
    ExportSnapshotError,
    LocalBinaryReference,
    ResolvedBinarySource,
    portable_name_key,
    portable_path_key,
    safe_join,
    safe_name,
    safe_relative_path,
)
from .staging_snapshot import (
    ExportDownloadPermissionError,
    ExportSelectionNotFoundError,
    ExportSnapshot,
)

MAX_ARCHIVE_UNITS = 1_000_000
MAX_ARCHIVE_MEDIA = 1_000_000


@dataclass(frozen=True, slots=True)
class ArchiveUnitRecord:
    """One requester-visible shared archive unit and its common metadata."""

    iri: str
    name: str
    parent_iri: str | None
    archive_level_iri: str
    media_iris: tuple[str, ...] = ()
    identifier: str = ""
    title: Mapping[str, str] | str = ""
    description: Mapping[str, str] | str = ""
    temporal: str = ""
    material_extent: Mapping[str, str] | str = ""
    creator_iris: tuple[str, ...] = ()
    provenance: Mapping[str, str] | str = ""
    conditions_of_access: Mapping[str, str] | str = ""
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ArchiveMediaRecord:
    """One visible archive medium linked from one or more archive units."""

    iri: str
    unit_iris: tuple[str, ...]
    access_mode: str
    original_name: str
    original_mime_type: str
    asset_id: str | None = None
    storage_path_candidate: str | None = None
    recorded_checksum: str | None = None
    external_source_url: str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class UnavailableArchiveMediaRecord:
    """One linked media IRI hidden by the requester's current permissions."""

    iri: str
    unit_iris: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AuthorizedArchiveInventory:
    """One permission-filtered archive read obtained with the requester."""

    units: tuple[ArchiveUnitRecord, ...]
    media: tuple[ArchiveMediaRecord, ...]
    unavailable_media: tuple[UnavailableArchiveMediaRecord, ...] = ()


class ArchiveInventoryReader(Protocol):
    """Read only archive resources visible through the supplied connection."""

    def read(
        self,
        connection: Any,
        *,
        project_short_name: str,
        profile: ExportProfile,
    ) -> AuthorizedArchiveInventory: ...


class ArchiveLabelResolver(Protocol):
    """Resolve requester-visible labels while preserving source IRIs."""

    def resolve(
        self,
        connection: Any,
        *,
        project_short_name: str,
        iris: set[str],
    ) -> Mapping[str, str]: ...


class OldapVisibleLabelResolver:
    """Resolve labels through the same permission-filtered OLDAP connection."""

    def resolve(
        self,
        connection: Any,
        *,
        project_short_name: str,
        iris: set[str],
    ) -> Mapping[str, str]:
        """Return the first visible preferred label for every readable IRI."""

        factory = ResourceInstanceFactory(
            con=connection, project=Xsd_NCName(project_short_name, validate=True)
        )
        result: dict[str, str] = {}
        for iri in sorted(iris):
            try:
                instance = factory.read(Iri(iri, validate=True))
            except (OldapErrorNoPermission, OldapErrorNotFound):
                result[iri] = ""
                continue
            label = ""
            for property_name in ("schema:name", "skos:prefLabel", "rdfs:label"):
                values = instance.get(Xsd_QName(property_name, validate=False))
                if values:
                    label = _preferred_text(values)
                    if label:
                        break
            result[iri] = label
        return result


class OldapArchiveInventoryReader:
    """Read requester-visible archive units and permitted media subclasses."""

    UNIT_PROPERTIES = {
        "schema:name",
        "shared:parentArchiveUnit",
        "shared:archiveLevel",
        "shared:hasMediaObject",
        "schema:identifier",
        "schema:description",
        "dcterms:temporal",
        "schema:materialExtent",
        "dcterms:creator",
        "dcterms:provenance",
        "schema:conditionsOfAccess",
    }
    MEDIA_PROPERTIES = {
        "shared:mediaAccessMode",
        "shared:assetId",
        "shared:originalName",
        "shared:originalMimeType",
        "shared:path",
        "shared:checksum",
        "shared:mediaUrl",
        "schema:url",
    }

    def __init__(self, label_resolver: ArchiveLabelResolver | None = None) -> None:
        self._labels = label_resolver or OldapVisibleLabelResolver()

    def read(
        self,
        connection: Any,
        *,
        project_short_name: str,
        profile: ExportProfile,
    ) -> AuthorizedArchiveInventory:
        """Return only units/media visible through the requester connection."""

        project = Xsd_NCName(project_short_name, validate=True)
        unit_properties = self.UNIT_PROPERTIES | {
            projection.property_iri for projection in profile.archive_units
        }
        unit_rows = ResourceInstance.search(
            con=connection,
            project=project,
            resClass=Xsd_QName("shared:ArchiveUnit", validate=False),
            includeProperties={
                _property_qname(name, connection) for name in unit_properties
            },
            limit=MAX_ARCHIVE_UNITS + 1,
        )
        if not isinstance(unit_rows, list):
            raise ExportSnapshotError("Unexpected ArchiveUnit search result.")
        if len(unit_rows) > MAX_ARCHIVE_UNITS:
            raise ExportSnapshotError("Visible archive units exceed the v1 bound.")

        links: dict[str, set[str]] = {}
        for row in unit_rows:
            unit_iri = _required_text(row, "iri", "Visible archive unit")
            for media_iri in _values(row, "shared:hasMediaObject"):
                links.setdefault(str(media_iri), set()).add(unit_iri)

        media_properties = self.MEDIA_PROPERTIES | {
            projection.property_iri for projection in profile.archive_media
        }
        media_by_iri: dict[str, Mapping[Any, Any]] = {}
        for class_name in profile.allowed_archive_media_classes:
            rows = ResourceInstance.search(
                con=connection,
                project=project,
                resClass=_property_qname(class_name, connection),
                includeProperties={
                    _property_qname(name, connection) for name in media_properties
                },
                limit=MAX_ARCHIVE_MEDIA + 1,
            )
            if not isinstance(rows, list):
                raise ExportSnapshotError("Unexpected archive media search result.")
            if len(rows) > MAX_ARCHIVE_MEDIA:
                raise ExportSnapshotError("Visible archive media exceeds the v1 bound.")
            for row in rows:
                media_iri = _required_text(row, "iri", "Visible archive media")
                if media_iri in links:
                    media_by_iri.setdefault(media_iri, row)
        if len(media_by_iri) > MAX_ARCHIVE_MEDIA:
            raise ExportSnapshotError("Visible archive media exceeds the v1 bound.")

        label_iris = _label_iris(unit_rows, profile.archive_units) | _label_iris(
            media_by_iri.values(), profile.archive_media
        )
        labels = (
            self._labels.resolve(
                connection,
                project_short_name=project_short_name,
                iris=label_iris,
            )
            if label_iris
            else {}
        )
        units = tuple(
            _archive_unit_record(row, profile.archive_units, labels)
            for row in unit_rows
        )
        media = tuple(
            _archive_media_record(
                row,
                tuple(sorted(links[media_iri])),
                profile.archive_media,
                labels,
            )
            for media_iri, row in sorted(media_by_iri.items())
        )
        unavailable = tuple(
            UnavailableArchiveMediaRecord(media_iri, tuple(sorted(unit_iris)))
            for media_iri, unit_iris in sorted(links.items())
            if media_iri not in media_by_iri
        )
        return AuthorizedArchiveInventory(units, media, unavailable)


class ArchiveSnapshotProjector:
    """Build safe ARCHIVE_UNIT and ARCHIVE_ALL manifests."""

    def __init__(
        self,
        inventory_reader: ArchiveInventoryReader,
        binary_resolver: BinarySourceResolver,
        *,
        max_archive_bytes: int = MAX_EXPORT_BYTES,
    ) -> None:
        self._inventory_reader = inventory_reader
        self._binary_resolver = binary_resolver
        if not 1 <= max_archive_bytes <= MAX_EXPORT_BYTES:
            raise ValueError("Archive export limit exceeds the v1 hard ceiling.")
        self._max_archive_bytes = max_archive_bytes

    def project(
        self,
        connection: Any,
        *,
        export_id: str,
        project_short_name: str,
        requested_by_iri: str,
        kind: ExportKind,
        selection_iri: str | None,
        profile: ExportProfile,
        generated_at: datetime,
        enforce_size_limit: bool = False,
    ) -> ExportSnapshot:
        """Read and freeze one requester-visible archive selection."""

        if kind not in {ExportKind.ARCHIVE_UNIT, ExportKind.ARCHIVE_ALL}:
            raise ExportSnapshotError("Archive projector received a non-Archive kind.")
        if profile.project_short_name != project_short_name:
            raise ExportSnapshotError("Export profile does not belong to the project.")
        inventory = self._inventory_reader.read(
            connection,
            project_short_name=project_short_name,
            profile=profile,
        )
        return self.project_inventory(
            export_id=export_id,
            kind=kind,
            selection_iri=selection_iri,
            profile=profile,
            generated_at=generated_at,
            inventory=inventory,
            requested_by_iri=requested_by_iri,
            enforce_size_limit=enforce_size_limit,
        )

    def project_inventory(
        self,
        *,
        export_id: str,
        kind: ExportKind,
        selection_iri: str | None,
        profile: ExportProfile,
        generated_at: datetime,
        inventory: AuthorizedArchiveInventory,
        requested_by_iri: str = "urn:oldap:system",
        enforce_size_limit: bool = False,
    ) -> ExportSnapshot:
        """Project an authorized inventory; exposed for deterministic tests."""

        if kind not in {ExportKind.ARCHIVE_UNIT, ExportKind.ARCHIVE_ALL}:
            raise ExportSnapshotError("Archive projector received a non-Archive kind.")
        units = _unique_units(inventory.units)
        selected, paths = _selected_unit_paths(kind, selection_iri, units)
        selected_media = [
            media
            for media in inventory.media
            if any(unit_iri in selected for unit_iri in media.unit_iris)
        ]
        if len(selected_media) > MAX_ARCHIVE_MEDIA:
            raise ExportSnapshotError("Visible archive media exceeds the v1 bound.")
        if any(
            media.access_mode not in {"local", "external"} for media in selected_media
        ):
            raise ExportSnapshotError(
                "Visible archive media has an unsupported access mode."
            )

        references = tuple(
            LocalBinaryReference(
                media_iri=media.iri,
                asset_id=media.asset_id or "",
                storage_path_candidate=media.storage_path_candidate or "",
                original_name=media.original_name,
            )
            for media in selected_media
            if media.access_mode == "local"
        )
        if any(
            not reference.asset_id or not reference.storage_path_candidate
            for reference in references
        ):
            raise ExportSnapshotError(
                "Local archive media has incomplete identity facts."
            )
        resolved = self._binary_resolver.resolve(references) if references else {}
        if set(resolved) != {reference.media_iri for reference in references}:
            raise ExportSnapshotError(
                "Media resolver returned an incomplete inventory."
            )

        entries: list[dict[str, Any]] = []
        source_bytes = 0
        included_count = 0
        for media in selected_media:
            linked = sorted(
                {unit_iri for unit_iri in media.unit_iris if unit_iri in selected},
                key=lambda unit_iri: portable_path_key(paths[unit_iri]),
            )
            if not linked:
                continue
            container_iri = linked[0]
            entry: dict[str, Any] = {
                "entryIndex": 0,
                "relativePath": safe_join(paths[container_iri], media.original_name),
                "mediaIri": media.iri,
                "containerIri": container_iri,
                "included": media.access_mode == "local",
                "metadata": {
                    **dict(media.metadata or {}),
                    "archive_unit_iris": linked,
                    "archive_unit_paths": [paths[unit_iri] for unit_iri in linked],
                },
            }
            if media.access_mode == "local":
                binary = resolved[media.iri]
                _validate_binary(media, binary)
                source_bytes += binary.size_bytes
                included_count += 1
                entry["binarySource"] = {
                    "assetId": binary.asset_id,
                    "storagePath": safe_relative_path(binary.storage_path),
                    "originalName": binary.original_name,
                    "originalMimeType": binary.original_mime_type,
                    **({"recordedChecksum": binary.sha256} if binary.sha256 else {}),
                    "expectedSizeBytes": binary.size_bytes,
                }
            else:
                entry["exclusionReason"] = "EXTERNAL_ORIGINAL_UNAVAILABLE"
                if media.external_source_url:
                    entry["externalSourceUrl"] = media.external_source_url
            entries.append(entry)
        for unavailable in inventory.unavailable_media:
            linked = sorted(
                {
                    unit_iri
                    for unit_iri in unavailable.unit_iris
                    if unit_iri in selected
                },
                key=lambda unit_iri: portable_path_key(paths[unit_iri]),
            )
            if not linked:
                continue
            container_iri = linked[0]
            opaque_name = (
                "unavailable-media-"
                f"{hashlib.sha256(unavailable.iri.encode('utf-8')).hexdigest()[:12]}.txt"
            )
            entries.append(
                {
                    "entryIndex": 0,
                    "relativePath": safe_join(paths[container_iri], opaque_name),
                    "mediaIri": unavailable.iri,
                    "containerIri": container_iri,
                    "included": False,
                    "exclusionReason": "ORIGINAL_NOT_EXPORTABLE",
                    "metadata": {
                        "archive_unit_iris": linked,
                        "archive_unit_paths": [paths[unit_iri] for unit_iri in linked],
                    },
                }
            )
        if enforce_size_limit and source_bytes > self._max_archive_bytes:
            raise ExportSizeLimitError(
                "Confirmed source bytes exceed the export limit."
            )

        entries.sort(key=lambda item: portable_path_key(item["relativePath"]))
        path_keys: set[str] = set()
        for index, entry in enumerate(entries):
            key = portable_path_key(entry["relativePath"])
            if key in path_keys:
                raise ExportSnapshotError("Archive media paths collide portably.")
            path_keys.add(key)
            entry["entryIndex"] = index

        directories = [
            {"relativePath": path, "containerIri": unit_iri}
            for unit_iri, path in paths.items()
        ]
        directories.sort(key=lambda item: portable_path_key(item["relativePath"]))
        archive_units = [
            _unit_manifest_entry(units[unit_iri], paths[unit_iri], selected)
            for unit_iri in sorted(
                selected, key=lambda item: portable_path_key(paths[item])
            )
        ]
        selection_name, selection_path = _selection_display(kind, selection_iri, units)
        profile_sha = hashlib.sha256(rfc8785.dumps(profile.to_dict())).hexdigest()
        selection = ExportSelectionSnapshot(
            project_short_name=profile.project_short_name,
            kind=kind,
            selection_iri=selection_iri,
            display_name=selection_name,
            display_path=selection_path,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            profile_sha256=profile_sha,
        )
        selection_value: dict[str, str] = {
            "displayName": selection_name,
            "displayPath": selection_path,
        }
        if selection_iri:
            selection_value["iri"] = selection_iri
        manifest = ExportManifest.from_dict(
            {
                "documentType": "oldap.zip-export.manifest",
                "schemaVersion": "1.0.0",
                "exportId": export_id,
                "generatedAt": generated_at.astimezone(UTC)
                .isoformat()
                .replace("+00:00", "Z"),
                "kind": kind.value,
                "projectShortName": profile.project_short_name,
                "requestedByIri": requested_by_iri,
                "profile": {
                    "profileId": profile.profile_id,
                    "profileVersion": profile.profile_version,
                    "profileSha256": profile_sha,
                    "metadataSchemaVersion": "1.0.0",
                },
                "selection": selection_value,
                "limits": {"maxArchiveBytes": self._max_archive_bytes},
                "directories": directories,
                "media": entries,
                "archiveUnits": archive_units,
            }
        )
        return ExportSnapshot(
            selection=selection,
            manifest=manifest,
            files_total=included_count,
            source_bytes=source_bytes,
            warning_count=len(entries) - included_count,
            max_archive_bytes=self._max_archive_bytes,
        )


class ArchiveDownloadAuthorizer:
    """Recheck the frozen archive hierarchy and every included source."""

    def __init__(self, inventory_reader: ArchiveInventoryReader, profile_registry: Any):
        self._inventory_reader = inventory_reader
        self._profiles = profile_registry

    def authorize(
        self,
        connection: Any,
        *,
        job: Any,
        manifest: ExportManifest,
    ) -> None:
        """Fail closed if profile, units, links, or media changed visibility."""

        if job.selection.kind not in {ExportKind.ARCHIVE_UNIT, ExportKind.ARCHIVE_ALL}:
            raise ExportDownloadPermissionError(
                "Export source authorization is unavailable."
            )
        try:
            profile = self._profiles.get_active(job.selection.project_short_name)
            profile_sha = hashlib.sha256(rfc8785.dumps(profile.to_dict())).hexdigest()
            if (
                profile.profile_id != job.selection.profile_id
                or profile.profile_version != job.selection.profile_version
                or profile_sha != job.selection.profile_sha256
            ):
                raise ExportDownloadPermissionError(
                    "Export profile is no longer available."
                )
            inventory = self._inventory_reader.read(
                connection,
                project_short_name=job.selection.project_short_name,
                profile=profile,
            )
        except (OldapErrorNoPermission, OldapErrorNotFound) as error:
            raise ExportDownloadPermissionError(
                "Export source authorization is no longer available."
            ) from error
        value = manifest.to_dict()
        try:
            current_units = _unique_units(inventory.units)
            current_selection, _ = _selected_unit_paths(
                job.selection.kind,
                job.selection.selection_iri,
                current_units,
            )
        except ExportSnapshotError as error:
            raise ExportDownloadPermissionError(
                "Export source authorization is no longer available."
            ) from error
        frozen_units = {unit["unitIri"] for unit in value.get("archiveUnits", [])}
        if not frozen_units or not frozen_units <= current_selection:
            raise ExportDownloadPermissionError(
                "Export source authorization is no longer available."
            )
        current_media = {media.iri: media for media in inventory.media}
        for item in value["media"]:
            if not item["included"]:
                continue
            media = current_media.get(item["mediaIri"])
            frozen_links = set(item["metadata"].get("archive_unit_iris", []))
            if (
                media is None
                or not frozen_links
                or not frozen_links <= frozen_units
                or not frozen_links <= set(media.unit_iris)
            ):
                raise ExportDownloadPermissionError(
                    "Export source authorization is no longer available."
                )


def _unique_units(
    values: tuple[ArchiveUnitRecord, ...],
) -> dict[str, ArchiveUnitRecord]:
    if len(values) > MAX_ARCHIVE_UNITS:
        raise ExportSnapshotError("Visible archive units exceed the v1 bound.")
    units: dict[str, ArchiveUnitRecord] = {}
    for unit in values:
        if unit.iri in units:
            raise ExportSnapshotError("Visible archive unit IRIs must be unique.")
        units[unit.iri] = unit
    return units


def _selected_unit_paths(
    kind: ExportKind,
    selection_iri: str | None,
    units: Mapping[str, ArchiveUnitRecord],
) -> tuple[set[str], dict[str, str]]:
    children: dict[str | None, list[ArchiveUnitRecord]] = {}
    for unit in units.values():
        children.setdefault(unit.parent_iri, []).append(unit)
    if kind is ExportKind.ARCHIVE_UNIT:
        root = units.get(selection_iri or "")
        if root is None:
            raise ExportSelectionNotFoundError("Selected archive unit was not found.")
        roots = (root,)
        selected = _descendants(root.iri, children) | {root.iri}
        initial = {root.iri: _safe_unit_name(root)}
    else:
        if selection_iri is not None:
            raise ExportSnapshotError("ARCHIVE_ALL must not contain selectionIri.")
        roots = tuple(unit for unit in units.values() if unit.parent_iri not in units)
        selected = set(units)
        initial = {
            unit.iri: safe_join("Archive", _safe_unit_name(unit)) for unit in roots
        }
    paths: dict[str, str] = {}
    active: set[str] = set()

    def visit(unit: ArchiveUnitRecord, path: str) -> None:
        if unit.iri in active or unit.iri in paths:
            raise ExportSnapshotError("Visible archive hierarchy contains a cycle.")
        active.add(unit.iri)
        paths[unit.iri] = path
        sibling_keys: set[str] = set()
        for child in sorted(
            children.get(unit.iri, ()), key=lambda item: item.name.casefold()
        ):
            if child.iri not in selected:
                continue
            key = portable_name_key(child.name)
            if key in sibling_keys:
                raise ExportSnapshotError(
                    "Visible archive sibling names collide portably."
                )
            sibling_keys.add(key)
            visit(child, safe_join(path, _safe_unit_name(child)))
        active.remove(unit.iri)

    root_keys: set[str] = set()
    for root in roots:
        key = portable_path_key(initial[root.iri])
        if key in root_keys:
            raise ExportSnapshotError("Visible archive root names collide portably.")
        root_keys.add(key)
        visit(root, initial[root.iri])
    if set(paths) != selected:
        raise ExportSnapshotError("Visible archive hierarchy has unreachable units.")
    return selected, paths


def _descendants(
    root: str,
    children: Mapping[str | None, list[ArchiveUnitRecord]],
) -> set[str]:
    result: set[str] = set()
    pending = [root]
    while pending:
        parent = pending.pop()
        for child in children.get(parent, ()):
            if child.iri in result or child.iri == root:
                raise ExportSnapshotError("Visible archive hierarchy contains a cycle.")
            result.add(child.iri)
            pending.append(child.iri)
    return result


def _selection_display(
    kind: ExportKind,
    selection_iri: str | None,
    units: Mapping[str, ArchiveUnitRecord],
) -> tuple[str, str]:
    if kind is ExportKind.ARCHIVE_ALL:
        return "Archive", "Archive"
    unit = units[selection_iri or ""]
    return unit.name, _safe_unit_name(unit)


def _safe_unit_name(unit: ArchiveUnitRecord) -> str:
    """Validate only selected ArchiveUnit path segments and identify bad source data."""

    try:
        return safe_name(unit.name)
    except ExportSnapshotError as error:
        raise ExportSnapshotError(
            f"ArchiveUnit name is unsafe for ZIP paths: {unit.name!r}."
        ) from error


def _unit_manifest_entry(
    unit: ArchiveUnitRecord,
    relative_path: str,
    selected: set[str],
) -> dict[str, Any]:
    return {
        "relativePath": relative_path,
        "unitIri": unit.iri,
        **({"parentUnitIri": unit.parent_iri} if unit.parent_iri in selected else {}),
        "archiveLevelIri": unit.archive_level_iri,
        "title": unit.title or unit.name,
        "identifier": unit.identifier,
        "description": unit.description,
        "temporal": unit.temporal,
        "materialExtent": unit.material_extent,
        "creatorIris": list(unit.creator_iris),
        "provenance": unit.provenance,
        "conditionsOfAccess": unit.conditions_of_access,
        "metadata": dict(unit.metadata or {}),
    }


def _validate_binary(media: ArchiveMediaRecord, resolved: ResolvedBinarySource) -> None:
    if (
        resolved.asset_id != media.asset_id
        or resolved.original_name != media.original_name
        or resolved.original_mime_type != media.original_mime_type
        or isinstance(resolved.size_bytes, bool)
        or not isinstance(resolved.size_bytes, int)
        or not 0 <= resolved.size_bytes <= MAX_EXPORT_BYTES
    ):
        raise ExportSnapshotError(
            "Media resolver facts differ from visible OLDAP data."
        )
    if media.recorded_checksum and resolved.sha256 != media.recorded_checksum:
        raise ExportSnapshotError(
            "Media resolver checksum differs from OLDAP evidence."
        )


def _archive_unit_record(
    row: Mapping[Any, Any],
    projections: tuple[ExportMetadataProjection, ...],
    labels: Mapping[str, str],
) -> ArchiveUnitRecord:
    iri = _required_text(row, "iri", "Visible archive unit")
    names = _values(row, "schema:name")
    level = _first(row, "shared:archiveLevel")
    if not names or level is None:
        raise ExportSnapshotError("Visible archive unit is incomplete.")
    return ArchiveUnitRecord(
        iri=iri,
        name=_preferred_text(names),
        parent_iri=_optional_text(_first(row, "shared:parentArchiveUnit")),
        archive_level_iri=str(level),
        media_iris=tuple(
            sorted(str(value) for value in _values(row, "shared:hasMediaObject"))
        ),
        identifier=_optional_text(_first(row, "schema:identifier")) or "",
        title=_lang_map(names),
        description=_lang_map(_values(row, "schema:description")),
        temporal=_optional_text(_first(row, "dcterms:temporal")) or "",
        material_extent=_lang_map(_values(row, "schema:materialExtent")),
        creator_iris=tuple(
            sorted(str(value) for value in _values(row, "dcterms:creator"))
        ),
        provenance=_lang_map(_values(row, "dcterms:provenance")),
        conditions_of_access=_lang_map(_values(row, "schema:conditionsOfAccess")),
        metadata={
            projection.column_name: _projected_value(row, projection, labels)
            for projection in projections
        },
    )


def _archive_media_record(
    row: Mapping[Any, Any],
    unit_iris: tuple[str, ...],
    projections: tuple[ExportMetadataProjection, ...],
    labels: Mapping[str, str],
) -> ArchiveMediaRecord:
    iri = _required_text(row, "iri", "Visible archive media")
    mode = (_optional_text(_first(row, "shared:mediaAccessMode")) or "").casefold()
    name = _optional_text(_first(row, "shared:originalName"))
    mime = _optional_text(_first(row, "shared:originalMimeType"))
    if mode == "external":
        name = name or (
            f"external-media-{hashlib.sha256(iri.encode('utf-8')).hexdigest()[:12]}.txt"
        )
        mime = mime or "application/octet-stream"
    if not name or not mime:
        raise ExportSnapshotError("Visible local archive media is incomplete.")
    return ArchiveMediaRecord(
        iri=iri,
        unit_iris=unit_iris,
        access_mode=mode,
        original_name=name,
        original_mime_type=mime,
        asset_id=_optional_text(_first(row, "shared:assetId")),
        storage_path_candidate=_optional_text(_first(row, "shared:path")),
        recorded_checksum=_optional_text(_first(row, "shared:checksum")),
        external_source_url=(
            _optional_text(_first(row, "shared:mediaUrl"))
            or _optional_text(_first(row, "schema:url"))
        ),
        metadata={
            projection.column_name: _projected_value(row, projection, labels)
            for projection in projections
        },
    )


def _label_iris(
    rows: Any,
    projections: tuple[ExportMetadataProjection, ...],
) -> set[str]:
    result: set[str] = set()
    for row in rows:
        for projection in projections:
            if projection.resolve_labels:
                result.update(
                    str(value) for value in _values(row, projection.property_iri)
                )
    return result


def _projected_value(
    row: Mapping[Any, Any],
    projection: ExportMetadataProjection,
    labels: Mapping[str, str],
) -> Any:
    values = _values(row, projection.property_iri)
    if projection.resolve_labels:
        return {str(value): labels.get(str(value), "") for value in values}
    if projection.value_shape == "iri-list":
        return sorted(str(value) for value in values)
    if projection.value_shape == "value-list":
        return [str(value) for value in values]
    if projection.value_shape == "lang-map":
        return _lang_map(values)
    if not values:
        return ""
    value = values[0]
    if isinstance(value, Xsd_boolean):
        return bool(value)
    if isinstance(value, Xsd_integer):
        return int(value)
    if isinstance(value, FloatingPoint):
        return float(value)
    if isinstance(value, (bool, int, float)):
        return value
    return str(value)


def _values(row: Mapping[Any, Any], property_name: str) -> list[Any]:
    raw = next((value for key, value in row.items() if str(key) == property_name), None)
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return list(raw)
    return [raw]


def _first(row: Mapping[Any, Any], property_name: str) -> Any | None:
    values = _values(row, property_name)
    return values[0] if values else None


def _required_text(row: Mapping[Any, Any], property_name: str, subject: str) -> str:
    value = _first(row, property_name)
    if value is None or not str(value):
        raise ExportSnapshotError(f"{subject} is incomplete.")
    return str(value)


def _optional_text(value: Any | None) -> str | None:
    return _lexical_text(value) if value is not None else None


def _lang_map(values: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        language = getattr(value, "lang", None)
        key = str(language).split(".")[-1].lower() if language else "und"
        result[key] = _lexical_text(value)
    return result


def _lexical_text(value: Any) -> str:
    """Return an OLDAP scalar's lexical value without a language suffix."""

    lexical = getattr(value, "value", None)
    return str(lexical) if lexical is not None else str(value)


def _preferred_text(values: Any) -> str:
    mapped = _lang_map(values)
    for language in ("de", "en", "fr", "it", "und"):
        if mapped.get(language):
            return mapped[language]
    return next(iter(mapped.values()), "")


def _property_qname(value: str, connection: Any) -> Xsd_QName:
    if value.startswith(("http://", "https://")):
        qname = Context(name=connection.context_name).iri2qname(value)
        if qname is None:
            raise ExportSnapshotError(
                "Profile resource is not available in the OLDAP context."
            )
        return qname
    return Xsd_QName(value, validate=False)


__all__ = [
    "ArchiveDownloadAuthorizer",
    "ArchiveInventoryReader",
    "ArchiveMediaRecord",
    "ArchiveSnapshotProjector",
    "ArchiveUnitRecord",
    "AuthorizedArchiveInventory",
    "OldapArchiveInventoryReader",
    "OldapVisibleLabelResolver",
    "UnavailableArchiveMediaRecord",
]
