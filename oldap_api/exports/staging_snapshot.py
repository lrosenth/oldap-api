"""Authorized Staging inventory projection into immutable export manifests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, Protocol

import rfc8785
from oldaplib.src.helpers.oldaperror import (
    OldapErrorNoPermission,
    OldapErrorNotFound,
    OldapErrorValue,
)
from oldaplib.src.helpers.context import Context
from oldaplib.src.objectfactory import (
    CompOp,
    ResourceInstance,
    ResourceInstanceFactory,
    SearchFilter,
)
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
    portable_name_key as _portable_name_key,
    portable_path_key as _portable_path_key,
    safe_join as _safe_join,
    safe_name as _safe_name,
    safe_relative_path as _safe_relative_path,
)

MAX_STAGING_FOLDERS = 100_000
MAX_STAGING_MEDIA = 1_000_000
SYSTEM_TOP = "top"
SYSTEM_TRASH = "trash"


class ExportSelectionNotFoundError(ExportSnapshotError):
    """Raised when the selected area/folder is absent or not visible."""


class ExportDownloadPermissionError(PermissionError):
    """Raised when an owner can no longer read every frozen source resource."""


@dataclass(frozen=True, slots=True)
class StagingAreaRecord:
    """Visible StagingArea identity required by the generic projector."""

    iri: str
    name: str


@dataclass(frozen=True, slots=True)
class StagingFolderRecord:
    """Visible folder relationship returned through the user connection."""

    iri: str
    name: str
    parent_iri: str | None


@dataclass(frozen=True, slots=True)
class StagingMediaRecord:
    """Visible media metadata without trusted filesystem facts."""

    iri: str
    folder_iri: str
    access_mode: str
    original_name: str
    original_mime_type: str
    asset_id: str | None = None
    storage_path_candidate: str | None = None
    recorded_checksum: str | None = None
    external_source_url: str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AuthorizedStagingInventory:
    """One permission-filtered Staging read obtained with the requester identity."""

    area: StagingAreaRecord
    folders: tuple[StagingFolderRecord, ...]
    media: tuple[StagingMediaRecord, ...]


class StagingInventoryReader(Protocol):
    """Read only resources visible through the supplied user connection."""

    def read(
        self,
        connection: Any,
        *,
        project_short_name: str,
        kind: ExportKind,
        selection_iri: str,
        profile: ExportProfile,
    ) -> AuthorizedStagingInventory: ...


@dataclass(frozen=True, slots=True)
class ExportSnapshot:
    """Bound selection, immutable manifest, and confirmed source totals."""

    selection: ExportSelectionSnapshot
    manifest: ExportManifest
    files_total: int
    source_bytes: int
    warning_count: int
    max_archive_bytes: int = MAX_EXPORT_BYTES

    def estimate_dict(self) -> dict[str, Any]:
        """Return the public read-only estimate contract."""

        return {
            "projectShortName": self.selection.project_short_name,
            "kind": self.selection.kind.value,
            **(
                {"selectionIri": self.selection.selection_iri}
                if self.selection.selection_iri
                else {}
            ),
            "displayName": self.selection.display_name,
            "displayPath": self.selection.display_path,
            "filesTotal": self.files_total,
            "sourceBytes": self.source_bytes,
            "warningCount": self.warning_count,
            "exceedsLimit": self.source_bytes > self.max_archive_bytes,
            "maxArchiveBytes": self.max_archive_bytes,
        }


class OldapStagingInventoryReader:
    """Read a permission-filtered StagingArea through oldaplib search APIs."""

    def read(
        self,
        connection: Any,
        *,
        project_short_name: str,
        kind: ExportKind,
        selection_iri: str,
        profile: ExportProfile,
    ) -> AuthorizedStagingInventory:
        """Return visible area, folders, and media using the requester identity."""

        if any(item.resolve_labels for item in profile.staging_media):
            raise ExportSnapshotError(
                "Staging metadata label resolution is not implemented in v1."
            )
        project = Xsd_NCName(project_short_name, validate=True)
        factory = ResourceInstanceFactory(con=connection, project=project)
        selected_iri = Iri(selection_iri, validate=True)
        if kind is ExportKind.STAGING_FOLDER:
            selected_folder = factory.read(selected_iri)
            if not _class_is_or_extends(
                selected_folder, Xsd_QName("shared:StagingFolder", validate=False)
            ):
                raise ExportSelectionNotFoundError(
                    "Selected Staging folder was not found."
                )
            raw_area_iri = _single_instance_value(
                selected_folder, "shared:inStagingArea"
            )
            if raw_area_iri is None:
                raise ExportSnapshotError("Selected Staging folder has no area.")
            area_iri = Iri(raw_area_iri, validate=True)
        elif kind is ExportKind.STAGING_ALL:
            area_iri = selected_iri
        else:
            raise ExportSnapshotError("Staging reader received a non-Staging kind.")
        area = factory.read(area_iri)
        if not _class_is_or_extends(
            area, Xsd_QName("shared:StagingArea", validate=False)
        ):
            raise ExportSelectionNotFoundError("Selected StagingArea was not found.")
        area_name = _single_instance_value(area, "schema:name")
        if area_name is None:
            raise ExportSnapshotError("Visible StagingArea has no name.")

        area_filter = [
            SearchFilter(
                prop=Xsd_QName("shared:inStagingArea", validate=False),
                op=CompOp.EQ,
                value=area_iri,
            )
        ]
        folder_rows = ResourceInstance.search(
            con=connection,
            project=project,
            resClass=Xsd_QName("shared:StagingFolder", validate=False),
            includeProperties={
                Xsd_QName("schema:name", validate=False),
                Xsd_QName("shared:inStagingFolder", validate=False),
            },
            filter=area_filter,
            limit=MAX_STAGING_FOLDERS + 1,
        )
        media_properties = {
            "shared:inStagingFolder",
            "shared:mediaAccessMode",
            "shared:assetId",
            "shared:originalName",
            "shared:originalMimeType",
            "shared:path",
            "shared:checksum",
            "shared:mediaUrl",
        }
        media_properties.update(item.property_iri for item in profile.staging_media)
        media_rows = ResourceInstance.search(
            con=connection,
            project=project,
            resClass=Xsd_QName("shared:StagingMediaObject", validate=False),
            includeProperties={
                _property_qname(name, connection) for name in media_properties
            },
            filter=area_filter,
            limit=MAX_STAGING_MEDIA + 1,
        )
        if not isinstance(folder_rows, list) or not isinstance(media_rows, list):
            raise OldapErrorValue("Unexpected Staging search result.")
        if (
            len(folder_rows) > MAX_STAGING_FOLDERS
            or len(media_rows) > MAX_STAGING_MEDIA
        ):
            raise ExportSnapshotError("Visible Staging inventory exceeds the v1 bound.")

        folders = tuple(_folder_record(row) for row in folder_rows)
        media = tuple(_media_record(row, profile.staging_media) for row in media_rows)
        return AuthorizedStagingInventory(
            area=StagingAreaRecord(str(area_iri), str(area_name)),
            folders=folders,
            media=media,
        )


class StagingSnapshotProjector:
    """Build safe Staging manifests from authorized OLDAP and media facts."""

    def __init__(
        self,
        inventory_reader: StagingInventoryReader,
        binary_resolver: BinarySourceResolver,
        *,
        max_archive_bytes: int = MAX_EXPORT_BYTES,
    ) -> None:
        self._inventory_reader = inventory_reader
        self._binary_resolver = binary_resolver
        if not 1 <= max_archive_bytes <= MAX_EXPORT_BYTES:
            raise ValueError("Staging export limit exceeds the v1 hard ceiling.")
        self._max_archive_bytes = max_archive_bytes

    def project(
        self,
        connection: Any,
        *,
        export_id: str,
        project_short_name: str,
        requested_by_iri: str,
        kind: ExportKind,
        selection_iri: str,
        profile: ExportProfile,
        generated_at: datetime,
        enforce_size_limit: bool = False,
    ) -> ExportSnapshot:
        """Build one immutable STAGING_FOLDER or STAGING_ALL snapshot."""

        if kind not in {ExportKind.STAGING_FOLDER, ExportKind.STAGING_ALL}:
            raise ExportSnapshotError("Staging projector received a non-Staging kind.")
        if profile.project_short_name != project_short_name:
            raise ExportSnapshotError("Export profile does not belong to the project.")
        inventory = self._inventory_reader.read(
            connection,
            project_short_name=project_short_name,
            kind=kind,
            selection_iri=selection_iri,
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
        selection_iri: str,
        profile: ExportProfile,
        generated_at: datetime,
        inventory: AuthorizedStagingInventory,
        requested_by_iri: str = "urn:oldap:system",
        enforce_size_limit: bool = False,
    ) -> ExportSnapshot:
        """Project an already authorized inventory; exposed for deterministic tests."""

        folders = _unique_folders(inventory.folders)
        selected, path_by_folder = _selected_folder_paths(
            kind, selection_iri, inventory.area, folders
        )
        visible_media = [
            item for item in inventory.media if item.folder_iri in selected
        ]
        if any(item.access_mode not in {"local", "external"} for item in visible_media):
            raise ExportSnapshotError("Visible media has an unsupported access mode.")
        references = tuple(
            LocalBinaryReference(
                media_iri=item.iri,
                asset_id=item.asset_id or "",
                storage_path_candidate=item.storage_path_candidate or "",
                original_name=item.original_name,
            )
            for item in visible_media
            if item.access_mode == "local"
        )
        if any(
            not item.asset_id or not item.storage_path_candidate for item in references
        ):
            raise ExportSnapshotError(
                "Local media has incomplete OLDAP identity facts."
            )
        resolved = self._binary_resolver.resolve(references) if references else {}
        if set(resolved) != {item.media_iri for item in references}:
            raise ExportSnapshotError(
                "Media resolver returned an incomplete inventory."
            )

        media_entries: list[dict[str, Any]] = []
        source_bytes = 0
        included_count = 0
        for item in visible_media:
            parent_path = path_by_folder[item.folder_iri]
            relative_path = _safe_join(parent_path, item.original_name)
            entry: dict[str, Any] = {
                "entryIndex": 0,
                "relativePath": relative_path,
                "mediaIri": item.iri,
                "containerIri": item.folder_iri,
                "included": item.access_mode == "local",
                "metadata": dict(item.metadata or {}),
            }
            if item.access_mode == "local":
                binary = resolved[item.iri]
                _validate_resolved_binary(item, binary)
                source_bytes += binary.size_bytes
                included_count += 1
                entry["binarySource"] = {
                    "assetId": binary.asset_id,
                    "storagePath": _safe_relative_path(binary.storage_path),
                    "originalName": binary.original_name,
                    "originalMimeType": binary.original_mime_type,
                    **({"recordedChecksum": binary.sha256} if binary.sha256 else {}),
                    "expectedSizeBytes": binary.size_bytes,
                }
            else:
                entry["exclusionReason"] = "EXTERNAL_ORIGINAL_UNAVAILABLE"
                if item.external_source_url:
                    entry["externalSourceUrl"] = item.external_source_url
            media_entries.append(entry)
        if enforce_size_limit and source_bytes > self._max_archive_bytes:
            raise ExportSizeLimitError(
                "Confirmed source bytes exceed the export limit."
            )

        media_entries.sort(key=lambda item: _portable_path_key(item["relativePath"]))
        _reject_portable_path_collisions(media_entries)
        for index, entry in enumerate(media_entries):
            entry["entryIndex"] = index

        directory_entries = [
            {"relativePath": path, "containerIri": iri}
            for iri, path in path_by_folder.items()
        ]
        directory_entries.sort(
            key=lambda item: _portable_path_key(item["relativePath"])
        )
        if len(
            {_portable_path_key(item["relativePath"]) for item in directory_entries}
        ) != len(directory_entries):
            raise ExportSnapshotError(
                "Directory paths collide on portable filesystems."
            )
        directory_keys = {
            _portable_path_key(item["relativePath"]) for item in directory_entries
        }
        if any(
            _portable_path_key(item["relativePath"]) in directory_keys
            for item in media_entries
        ):
            raise ExportSnapshotError("Media and directory paths collide portably.")
        selection_name, selection_path = _selection_display(
            kind, selection_iri, inventory.area, folders, path_by_folder
        )
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
                "selection": {
                    "iri": selection_iri,
                    "displayName": selection_name,
                    "displayPath": selection_path,
                },
                "limits": {"maxArchiveBytes": self._max_archive_bytes},
                "directories": directory_entries,
                "media": media_entries,
            }
        )
        return ExportSnapshot(
            selection=selection,
            manifest=manifest,
            files_total=included_count,
            source_bytes=source_bytes,
            warning_count=len(media_entries) - included_count,
            max_archive_bytes=self._max_archive_bytes,
        )


class StagingDownloadAuthorizer:
    """Recheck current source visibility before issuing a download capability."""

    def __init__(self, inventory_reader: StagingInventoryReader) -> None:
        self._inventory_reader = inventory_reader

    def authorize(
        self,
        connection: Any,
        *,
        job: Any,
        manifest: ExportManifest,
    ) -> None:
        """Require every frozen included StagingMediaObject to remain visible."""

        if (
            job.selection.kind
            not in {ExportKind.STAGING_FOLDER, ExportKind.STAGING_ALL}
            or not job.selection.selection_iri
        ):
            raise ExportDownloadPermissionError(
                "Export source authorization is unavailable."
            )
        profile = ExportProfile(
            profile_id=job.selection.profile_id,
            profile_version=job.selection.profile_version,
            project_short_name=job.selection.project_short_name,
            allowed_archive_media_classes=("shared:MediaObject",),
        )
        try:
            inventory = self._inventory_reader.read(
                connection,
                project_short_name=job.selection.project_short_name,
                kind=job.selection.kind,
                selection_iri=job.selection.selection_iri,
                profile=profile,
            )
            folders = _unique_folders(inventory.folders)
            selected, _ = _selected_folder_paths(
                job.selection.kind,
                job.selection.selection_iri,
                inventory.area,
                folders,
            )
        except (OldapErrorNoPermission, OldapErrorNotFound) as error:
            raise ExportDownloadPermissionError(
                "Export source authorization is no longer available."
            ) from error
        visible = {item.iri for item in inventory.media if item.folder_iri in selected}
        frozen = {
            str(item["mediaIri"])
            for item in manifest.to_dict()["media"]
            if item["included"]
        }
        if not frozen <= visible:
            raise ExportDownloadPermissionError(
                "Export source authorization is no longer available."
            )


def _unique_folders(
    values: tuple[StagingFolderRecord, ...],
) -> dict[str, StagingFolderRecord]:
    result: dict[str, StagingFolderRecord] = {}
    for item in values:
        if item.iri in result:
            raise ExportSnapshotError("Visible Staging folder IRIs must be unique.")
        _safe_name(item.name)
        result[item.iri] = item
    return result


def _selected_folder_paths(
    kind: ExportKind,
    selection_iri: str,
    area: StagingAreaRecord,
    folders: Mapping[str, StagingFolderRecord],
) -> tuple[set[str], dict[str, str]]:
    children: dict[str | None, list[StagingFolderRecord]] = {}
    for folder in folders.values():
        children.setdefault(folder.parent_iri, []).append(folder)
    top = next(
        (
            item
            for item in folders.values()
            if item.parent_iri is None and _portable_name_key(item.name) == SYSTEM_TOP
        ),
        None,
    )
    trash_roots = {
        item.iri
        for item in folders.values()
        if _portable_name_key(item.name) == SYSTEM_TRASH
        and (top is None or item.parent_iri == top.iri)
    }
    excluded: set[str] = set()
    for root in trash_roots:
        excluded.update(_descendants(root, children))
        excluded.add(root)

    if kind is ExportKind.STAGING_FOLDER:
        root = folders.get(selection_iri)
        if root is None or root.iri in excluded:
            raise ExportSelectionNotFoundError("Selected Staging folder was not found.")
        selected = _descendants(root.iri, children) | {root.iri}
        selected -= excluded
        root_path = _safe_name(root.name)
        paths = _build_paths((root,), children, selected, {root.iri: root_path})
        return selected, paths

    if selection_iri != area.iri:
        raise ExportSelectionNotFoundError("Selected StagingArea was not found.")
    selected = set(folders) - excluded
    area_path = _safe_name(area.name)
    roots = [item for item in folders.values() if item.parent_iri not in selected]
    initial: dict[str, str] = {}
    for root in roots:
        initial[root.iri] = (
            area_path if root is top else _safe_join(area_path, _safe_name(root.name))
        )
    return selected, _build_paths(tuple(roots), children, selected, initial)


def _build_paths(
    roots: tuple[StagingFolderRecord, ...],
    children: Mapping[str | None, list[StagingFolderRecord]],
    selected: set[str],
    initial: dict[str, str],
) -> dict[str, str]:
    result: dict[str, str] = {}
    active: set[str] = set()

    def visit(folder: StagingFolderRecord, path: str) -> None:
        if folder.iri in active or folder.iri in result:
            raise ExportSnapshotError("Visible Staging hierarchy contains a cycle.")
        active.add(folder.iri)
        result[folder.iri] = path
        sibling_keys: set[str] = set()
        for child in sorted(
            children.get(folder.iri, ()), key=lambda item: item.name.casefold()
        ):
            if child.iri not in selected:
                continue
            key = _portable_name_key(child.name)
            if key in sibling_keys:
                raise ExportSnapshotError(
                    "Visible sibling folder names collide portably."
                )
            sibling_keys.add(key)
            visit(child, _safe_join(path, _safe_name(child.name)))
        active.remove(folder.iri)

    for root in roots:
        if root.iri in selected:
            visit(root, initial[root.iri])
    if set(result) != selected:
        raise ExportSnapshotError("Visible Staging hierarchy has unreachable folders.")
    return result


def _descendants(
    root: str, children: Mapping[str | None, list[StagingFolderRecord]]
) -> set[str]:
    result: set[str] = set()
    pending = [root]
    while pending:
        parent = pending.pop()
        for child in children.get(parent, ()):
            if child.iri in result or child.iri == root:
                raise ExportSnapshotError("Visible Staging hierarchy contains a cycle.")
            result.add(child.iri)
            pending.append(child.iri)
    return result


def _selection_display(
    kind: ExportKind,
    selection_iri: str,
    area: StagingAreaRecord,
    folders: Mapping[str, StagingFolderRecord],
    paths: Mapping[str, str],
) -> tuple[str, str]:
    if kind is ExportKind.STAGING_ALL:
        return area.name, _safe_name(area.name)
    folder = folders[selection_iri]
    return folder.name, paths[folder.iri]


def _validate_resolved_binary(
    media: StagingMediaRecord, resolved: ResolvedBinarySource
) -> None:
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


def _reject_portable_path_collisions(entries: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for entry in entries:
        key = _portable_path_key(entry["relativePath"])
        if key in seen:
            raise ExportSnapshotError("Media paths collide on portable filesystems.")
        seen.add(key)


def _folder_record(row: Mapping[Any, Any]) -> StagingFolderRecord:
    iri = _first(row, "iri")
    name = _first(row, "schema:name")
    if iri is None or name is None:
        raise ExportSnapshotError("Visible Staging folder is incomplete.")
    parent = _first(row, "shared:inStagingFolder")
    return StagingFolderRecord(
        iri=str(iri),
        name=str(name),
        parent_iri=str(parent) if parent is not None else None,
    )


def _media_record(
    row: Mapping[Any, Any], projections: tuple[ExportMetadataProjection, ...]
) -> StagingMediaRecord:
    iri = _first(row, "iri")
    folder = _first(row, "shared:inStagingFolder")
    mode = str(_first(row, "shared:mediaAccessMode") or "")
    name = _first(row, "shared:originalName")
    mime = _first(row, "shared:originalMimeType")
    if iri is None or folder is None or name is None or mime is None:
        raise ExportSnapshotError("Visible Staging media is incomplete.")
    return StagingMediaRecord(
        iri=str(iri),
        folder_iri=str(folder),
        access_mode=mode,
        original_name=str(name),
        original_mime_type=str(mime),
        asset_id=_optional_text(_first(row, "shared:assetId")),
        storage_path_candidate=_optional_text(_first(row, "shared:path")),
        recorded_checksum=_optional_text(_first(row, "shared:checksum")),
        external_source_url=_optional_text(_first(row, "shared:mediaUrl")),
        metadata={
            item.column_name: _projected_value(row, item) for item in projections
        },
    )


def _projected_value(
    row: Mapping[Any, Any], projection: ExportMetadataProjection
) -> Any:
    values = _values(row, projection.property_iri)
    if projection.value_shape in {"iri-list", "value-list"}:
        return [str(value) for value in values]
    if projection.value_shape == "lang-map":
        return {str(getattr(value, "lang", "und")): str(value) for value in values}
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


def _optional_text(value: Any | None) -> str | None:
    return str(value) if value is not None else None


def _property_qname(value: str, connection: Any) -> Xsd_QName:
    if value.startswith(("http://", "https://")):
        qname = Context(name=connection.context_name).iri2qname(value)
        if qname is None:
            raise ExportSnapshotError(
                "Profile metadata property is not available in the OLDAP context."
            )
        return qname
    return Xsd_QName(value, validate=False)


def _single_instance_value(instance: Any, property_name: str) -> Any | None:
    values = instance.get(Xsd_QName(property_name, validate=False))
    if not values:
        return None
    if len(values) != 1:
        raise ExportSnapshotError(f"{property_name} must be single-valued.")
    return next(iter(values))


def _class_is_or_extends(instance: Any, expected: Xsd_QName) -> bool:
    instance_class = instance.__class__
    if instance_class.name == expected:
        return True

    def contains(superclasses: Mapping[Any, Any]) -> bool:
        for iri, superclass in (superclasses or {}).items():
            if iri == expected:
                return True
            if superclass is not None and contains(
                getattr(superclass, "superclass", {})
            ):
                return True
        return False

    return contains(getattr(instance_class, "superclass", {}))
