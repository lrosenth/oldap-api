"""Shared safe primitives for project-neutral export snapshot projectors."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Mapping, Protocol


class ExportSnapshotError(ValueError):
    """Raised when visible source data cannot form one safe stable snapshot."""


class ExportSizeLimitError(ExportSnapshotError):
    """Raised when confirmed original bytes exceed the v1 archive ceiling."""


@dataclass(frozen=True, slots=True)
class LocalBinaryReference:
    """Untrusted RDF identity hints sent to the authoritative media resolver."""

    media_iri: str
    asset_id: str
    storage_path_candidate: str
    original_name: str


@dataclass(frozen=True, slots=True)
class ResolvedBinarySource:
    """Media-service-confirmed original facts safe for a worker manifest."""

    asset_id: str
    storage_path: str
    original_name: str
    original_mime_type: str
    size_bytes: int
    sha256: str | None = None


class BinarySourceResolver(Protocol):
    """Resolve local originals without trusting RDF paths in oldap-api."""

    def resolve(
        self, references: tuple[LocalBinaryReference, ...]
    ) -> Mapping[str, ResolvedBinarySource]: ...


def safe_join(parent: str, name: str) -> str:
    """Join one already safe path with one safe portable leaf name."""

    return safe_relative_path(f"{parent}/{safe_name(name)}")


def safe_relative_path(value: str) -> str:
    """Validate and normalize one NFC relative POSIX export path."""

    if not isinstance(value, str) or len(value.encode("utf-8")) > 4096:
        raise ExportSnapshotError("Export path is invalid.")
    if value != unicodedata.normalize("NFC", value) or "\\" in value or "\x00" in value:
        raise ExportSnapshotError("Export path is not canonical NFC POSIX text.")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ExportSnapshotError("Export path is unsafe.")
    for part in path.parts:
        safe_name(part)
    return path.as_posix()


def safe_name(value: str) -> str:
    """Validate one cross-platform-safe NFC path segment."""

    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
    }
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > 255
        or value != unicodedata.normalize("NFC", value)
        or any(character in value for character in ("/", "\\", "\x00"))
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or value.endswith((" ", "."))
        or value.split(".", maxsplit=1)[0].casefold() in reserved
    ):
        raise ExportSnapshotError("Export name is unsafe.")
    return value


def portable_name_key(value: str) -> str:
    """Return the collision key used by common portable filesystems."""

    return unicodedata.normalize("NFC", value).rstrip(" .").casefold()


def portable_path_key(value: str) -> str:
    """Return a component-wise portable collision key for one path."""

    return "/".join(portable_name_key(part) for part in PurePosixPath(value).parts)


__all__ = [
    "BinarySourceResolver",
    "ExportSizeLimitError",
    "ExportSnapshotError",
    "LocalBinaryReference",
    "ResolvedBinarySource",
    "portable_name_key",
    "portable_path_key",
    "safe_join",
    "safe_name",
    "safe_relative_path",
]
