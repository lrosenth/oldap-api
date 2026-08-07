"""Closed Phase 5 staging-commit contract and deterministic resource mapping."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID, uuid5

from .domain import ImportDomainError

MAX_COMMIT_ITEMS = 10_000
ASSET_ID_RE = re.compile(r"^[A-Za-z0-9._~-]{1,128}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ImportCommitConflict(ImportDomainError):
    """Raised when live staging state no longer permits a prepared commit."""

    code = "IMPORT_COMMIT_CONFLICT"


@dataclass(frozen=True, slots=True)
class FolderCommitItem:
    """One new staging folder derived from an explicit manifest directory."""

    entry_index: int
    relative_path: str
    parent_relative_path: str
    name: str
    resource_iri: str


@dataclass(frozen=True, slots=True)
class MediaCommitItem:
    """One already promoted, checksum-verified media asset registration."""

    entry_index: int
    relative_path: str
    parent_relative_path: str
    asset_id: str
    checksum_sha256: str
    original_name: str
    original_mime_type: str
    dcterms_type: str
    protocol: str
    derivative_name: str
    storage_path: str
    resource_iri: str


@dataclass(frozen=True, slots=True)
class ImportCommit:
    """Fully validated and deterministically mapped import commit request."""

    event_id: str
    claim_id: str
    expected_state_version: int
    manifest_sha256: str
    folders: tuple[FolderCommitItem, ...]
    media: tuple[MediaCommitItem, ...]
    digest: str

    @property
    def resources(self) -> tuple[dict[str, Any], ...]:
        """Return the stable public entry-to-resource mapping."""

        folders = (
            {
                "entryIndex": item.entry_index,
                "relativePath": item.relative_path,
                "resourceIri": item.resource_iri,
            }
            for item in self.folders
        )
        media = (
            {
                "entryIndex": item.entry_index,
                "relativePath": item.relative_path,
                "resourceIri": item.resource_iri,
                "assetId": item.asset_id,
            }
            for item in self.media
        )
        return tuple(
            sorted(
                (*folders, *media),
                key=lambda item: (item["relativePath"], "assetId" in item),
            )
        )


def validate_import_commit(import_id: str, value: Any, project: str) -> ImportCommit:
    """Validate the complete closed commit request before opening a transaction."""

    required = {
        "eventId",
        "claimId",
        "expectedStateVersion",
        "manifestSha256",
        "folders",
        "media",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("The import commit fields are invalid.")
    event_id = _canonical_uuid(value["eventId"], "eventId")
    claim_id = _canonical_uuid(value["claimId"], "claimId")
    version = value["expectedStateVersion"]
    manifest_sha256 = value["manifestSha256"]
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise ValueError("expectedStateVersion must be non-negative.")
    if not isinstance(manifest_sha256, str) or not SHA256_RE.fullmatch(manifest_sha256):
        raise ValueError("manifestSha256 must be a lower-case SHA-256 digest.")
    if not isinstance(value["folders"], list) or not isinstance(value["media"], list):
        raise ValueError("folders and media must be arrays.")
    if (
        not value["media"]
        or len(value["folders"]) + len(value["media"]) > MAX_COMMIT_ITEMS
    ):
        raise ValueError("The import commit item count is invalid.")

    namespace = UUID(import_id)
    folders = tuple(_folder(namespace, item) for item in value["folders"])
    media = tuple(_media(namespace, item, project) for item in value["media"])
    _validate_tree(folders, media)
    digest = hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return ImportCommit(
        event_id=event_id,
        claim_id=claim_id,
        expected_state_version=version,
        manifest_sha256=manifest_sha256,
        folders=folders,
        media=media,
        digest=digest,
    )


def _folder(namespace: UUID, value: Any) -> FolderCommitItem:
    required = {"entryIndex", "relativePath", "parentRelativePath", "name"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("A folder commit item is invalid.")
    index = _entry_index(value["entryIndex"])
    path = _path(value["relativePath"], allow_empty=False)
    raw_parent = _path(value["parentRelativePath"], allow_empty=True)
    parent = raw_parent if isinstance(raw_parent, str) else raw_parent.as_posix()
    name = _name(value["name"])
    if path.name != name or _parent(path) != parent:
        raise ValueError("A folder path decomposition is inconsistent.")
    return FolderCommitItem(
        entry_index=index,
        relative_path=path.as_posix(),
        parent_relative_path=parent,
        name=name,
        resource_iri=f"urn:uuid:{uuid5(namespace, f'folder:{path.as_posix()}')}",
    )


def _media(namespace: UUID, value: Any, project: str) -> MediaCommitItem:
    required = {
        "entryIndex",
        "relativePath",
        "parentRelativePath",
        "assetId",
        "checksumSha256",
        "originalName",
        "originalMimeType",
        "dctermsType",
        "protocol",
        "derivativeName",
        "storagePath",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("A media commit item is invalid.")
    index = _entry_index(value["entryIndex"])
    path = _path(value["relativePath"], allow_empty=False)
    raw_parent = _path(value["parentRelativePath"], allow_empty=True)
    parent = raw_parent if isinstance(raw_parent, str) else raw_parent.as_posix()
    name = _name(value["originalName"])
    expected_asset_id = str(uuid5(namespace, f"entry:{index}"))
    if (
        path.name != name
        or _parent(path) != parent
        or value["assetId"] != expected_asset_id
        or ASSET_ID_RE.fullmatch(str(value["assetId"])) is None
        or SHA256_RE.fullmatch(str(value["checksumSha256"])) is None
    ):
        raise ValueError("A media identity or path is inconsistent.")
    facts = {
        "image/jpeg": ("dcmitype:StillImage", "iiif", "master.tif", "image"),
        "image/tiff": ("dcmitype:StillImage", "iiif", "master.tif", "image"),
        "image/png": ("dcmitype:StillImage", "iiif", "master.tif", "image"),
        "audio/wav": ("dcmitype:Sound", "http", "web.mp3", "audio"),
        "audio/flac": ("dcmitype:Sound", "http", "web.mp3", "audio"),
        "audio/mpeg": ("dcmitype:Sound", "http", "web.mp3", "audio"),
        "video/mp4": ("dcmitype:MovingImage", "http", "web.mp4", "video"),
        "application/pdf": ("dcmitype:Text", "http", "document.pdf", "document"),
        "text/plain": ("dcmitype:Text", "http", "document.txt", "document"),
    }
    mime = value["originalMimeType"]
    if not isinstance(mime, str) or mime not in facts:
        raise ValueError("A media MIME type is unsupported.")
    dcterms_type, protocol, derivative, media_type = facts[mime]
    if (
        value["dctermsType"] != dcterms_type
        or value["protocol"] != protocol
        or value["derivativeName"] != derivative
        or value["storagePath"] != f"{project}/{media_type}"
    ):
        raise ValueError("Media delivery facts differ from the closed MVP mapping.")
    return MediaCommitItem(
        entry_index=index,
        relative_path=path.as_posix(),
        parent_relative_path=parent,
        asset_id=expected_asset_id,
        checksum_sha256=value["checksumSha256"],
        original_name=name,
        original_mime_type=mime,
        dcterms_type=dcterms_type,
        protocol=protocol,
        derivative_name=derivative,
        storage_path=value["storagePath"],
        resource_iri=f"urn:uuid:{uuid5(namespace, f'media:{path.as_posix()}')}",
    )


def _validate_tree(
    folders: tuple[FolderCommitItem, ...], media: tuple[MediaCommitItem, ...]
) -> None:
    folder_paths = {item.relative_path for item in folders}
    if len(folder_paths) != len(folders):
        raise ValueError("Folder paths must be unique.")
    media_indexes = [item.entry_index for item in media]
    media_paths = [item.relative_path for item in media]
    asset_ids = [item.asset_id for item in media]
    if (
        len(set(media_indexes)) != len(media_indexes)
        or len(set(media_paths)) != len(media_paths)
        or len(set(asset_ids)) != len(asset_ids)
    ):
        raise ValueError("Media indexes, paths, and asset IDs must be unique.")
    for item in (*folders, *media):
        if item.parent_relative_path and item.parent_relative_path not in folder_paths:
            raise ValueError(
                "Every non-root item must reference a committed parent folder."
            )
    siblings: set[tuple[str, str]] = set()
    for item in (*folders, *media):
        name = item.name if isinstance(item, FolderCommitItem) else item.original_name
        key = (item.parent_relative_path, _portable_name_key(name))
        if key in siblings:
            raise ValueError("Sibling names must be portable and unique.")
        siblings.add(key)


def _entry_index(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 9_999:
        raise ValueError("entryIndex is invalid.")
    return value


def _path(value: Any, *, allow_empty: bool) -> PurePosixPath | str:
    if allow_empty and value == "":
        return ""
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 1_024:
        raise ValueError("A relative path is invalid.")
    if value != unicodedata.normalize("NFC", value) or "\\" in value or "\x00" in value:
        raise ValueError("A relative path is not canonical NFC POSIX text.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("A relative path is unsafe.")
    for part in path.parts:
        _name(part)
    return path


def _parent(path: PurePosixPath) -> str:
    return "" if str(path.parent) == "." else path.parent.as_posix()


def _name(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > 255
        or value != unicodedata.normalize("NFC", value)
        or any(character in value for character in ("/", "\\", "\x00"))
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or value.endswith((" ", "."))
    ):
        raise ValueError("A resource name is invalid.")
    return value


def _portable_name_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).rstrip(" .").casefold()


def _canonical_uuid(value: Any, field: str) -> str:
    try:
        canonical = str(UUID(str(value)))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be a UUID.") from error
    if value != canonical:
        raise ValueError(f"{field} must be a canonical UUID.")
    return canonical
