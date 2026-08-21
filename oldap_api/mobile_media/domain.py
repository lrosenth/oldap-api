"""Closed mobile-media commit contract and deterministic resource identity."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

import rfc8785

MAX_ORIGINAL_BYTES = 100 * 1024 * 1024
MAX_ORIGINAL_NAME_BYTES = 255
MAX_COMMENT_CHARACTERS = 2_000
CHECKSUM_RE = re.compile(r"^sha256:([0-9a-f]{64})$")
SUPPORTED_IMAGE_MIME_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/heic", "image/heif"}
)
EXPECTED_DERIVATIVES = ("master.tif",)


class MobileMediaError(Exception):
    """Base class for stable internal mobile-media failures."""

    code = "internal_error"
    status = 500
    retryable = False


class MobileMediaValidationError(MobileMediaError, ValueError):
    """Raised before a malformed closed commit reaches persistence."""

    code = "validation_failed"
    status = 400


class MobileMediaPermissionDeniedError(MobileMediaError, PermissionError):
    """Hide whether account, membership, role, or area authorization failed."""

    code = "staging_area_not_permitted"
    status = 403


class MobileMediaUploadPermissionDeniedError(MobileMediaError, PermissionError):
    """Raised when current project-level media creation is unavailable."""

    code = "staging_upload_not_permitted"
    status = 403


class MobileMediaInboxNotFoundError(MobileMediaError, LookupError):
    """Raised when the exact root top/direct Mobile destination is absent."""

    code = "staging_folder_not_found"
    status = 404


class MobileMediaInboxNotProtectedError(MobileMediaError):
    """Raised when the mobile inbox is ambiguous or no longer read-only."""

    code = "staging_folder_not_protected"
    status = 409


class MobileMediaCommitConflict(MobileMediaError):
    """Reject conflicting event, upload, asset, or resource reuse opaquely."""

    code = "client_asset_conflict"
    status = 409


class MobileMediaDestinationChangedError(MobileMediaError):
    """Reject publication evidence for a no-longer-current storage path."""

    code = "staging_destination_changed"
    status = 409


class MobileMediaServiceUnavailableError(MobileMediaError):
    """Hide internal persistence or configuration details from the caller."""

    code = "upstream_unavailable"
    status = 503
    retryable = True


@dataclass(frozen=True, slots=True)
class PublicationEvidence:
    """Media-server assertion that upload-owned final files are durable."""

    owner_upload_id: str
    asset_id: str
    byte_length: int
    checksum: str
    derivative_names: tuple[str, ...]
    storage_path: str

    def to_dict(self) -> dict[str, Any]:
        """Return the closed wire representation included in the request hash."""

        return {
            "ownerUploadId": self.owner_upload_id,
            "assetId": self.asset_id,
            "byteLength": self.byte_length,
            "checksum": self.checksum,
            "derivativeNames": list(self.derivative_names),
            "storagePath": self.storage_path,
        }


@dataclass(frozen=True, slots=True)
class MobileMediaCommit:
    """Validated immutable facts accepted from the trusted media service."""

    event_id: str
    upload_id: str
    client_asset_id: str
    owner_user_iri: str
    staging_area_id: str
    original_name: str
    original_mime_type: str
    byte_length: int
    checksum: str
    comment: str | None
    publication: PublicationEvidence
    request_digest: str

    @property
    def checksum_sha256(self) -> str:
        """Return the lower-case digest used by existing OLDAP media resources."""

        return self.checksum.removeprefix("sha256:")

    @property
    def resource_iri(self) -> str:
        """Derive one deployment-independent resource IRI from clientAssetId."""

        value = uuid5(
            NAMESPACE_URL, f"https://oldap.org/mobile-media/{self.client_asset_id}"
        )
        return f"urn:uuid:{value}"

    @property
    def receipt_iri(self) -> str:
        """Derive the global permanent receipt identity from clientAssetId."""

        return f"urn:oldap:mobile-media-commit:{self.client_asset_id}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return the normalized closed body used for RFC-8785 hashing."""

        result: dict[str, Any] = {
            "eventId": self.event_id,
            "uploadId": self.upload_id,
            "clientAssetId": self.client_asset_id,
            "ownerUserIri": self.owner_user_iri,
            "stagingAreaId": self.staging_area_id,
            "originalName": self.original_name,
            "originalMimeType": self.original_mime_type,
            "byteLength": self.byte_length,
            "checksum": self.checksum,
            "publication": self.publication.to_dict(),
        }
        if self.comment is not None:
            result["comment"] = self.comment
        return result


@dataclass(frozen=True, slots=True)
class MobileMediaCommitResult:
    """Permanent replayable OLDAP resource mapping returned to media."""

    event_id: str
    upload_id: str
    client_asset_id: str
    staging_area_id: str
    asset_id: str
    resource_iri: str
    checksum: str
    committed_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Return the stable internal JSON result."""

        return {
            "eventId": self.event_id,
            "uploadId": self.upload_id,
            "clientAssetId": self.client_asset_id,
            "stagingAreaId": self.staging_area_id,
            "assetId": self.asset_id,
            "resourceIri": self.resource_iri,
            "checksum": self.checksum,
            "committedAt": self.committed_at.astimezone(UTC)
            .isoformat()
            .replace("+00:00", "Z"),
        }

    @classmethod
    def from_dict(cls, value: Any) -> MobileMediaCommitResult:
        """Restore and revalidate a permanent receipt result."""

        required = {
            "eventId",
            "uploadId",
            "clientAssetId",
            "stagingAreaId",
            "assetId",
            "resourceIri",
            "checksum",
            "committedAt",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError("Stored mobile-media result is invalid.")
        committed_at = datetime.fromisoformat(
            str(value["committedAt"]).replace("Z", "+00:00")
        )
        if committed_at.tzinfo is None:
            raise ValueError("Stored mobile-media result timestamp is invalid.")
        return cls(
            event_id=_canonical_uuid(value["eventId"], "eventId"),
            upload_id=_canonical_uuid(value["uploadId"], "uploadId"),
            client_asset_id=_canonical_uuid(value["clientAssetId"], "clientAssetId"),
            staging_area_id=_absolute_iri(value["stagingAreaId"], "stagingAreaId"),
            asset_id=_canonical_uuid(value["assetId"], "assetId"),
            resource_iri=_absolute_iri(value["resourceIri"], "resourceIri"),
            checksum=_checksum(value["checksum"]),
            committed_at=committed_at.astimezone(UTC),
        )


def validate_mobile_media_commit(upload_id: str, value: Any) -> MobileMediaCommit:
    """Validate and canonicalize the exact internal commit request."""

    required = {
        "eventId",
        "uploadId",
        "clientAssetId",
        "ownerUserIri",
        "stagingAreaId",
        "originalName",
        "originalMimeType",
        "byteLength",
        "checksum",
        "publication",
    }
    allowed = required | {"comment"}
    if (
        not isinstance(value, dict)
        or not required <= set(value)
        or set(value) > allowed
    ):
        raise MobileMediaValidationError("The mobile-media commit fields are invalid.")

    path_upload_id = _canonical_uuid(upload_id, "uploadId")
    body_upload_id = _canonical_uuid(value["uploadId"], "uploadId")
    if body_upload_id != path_upload_id:
        raise MobileMediaValidationError("The uploadId does not match the route.")
    client_asset_id = _canonical_uuid(value["clientAssetId"], "clientAssetId")
    checksum = _checksum(value["checksum"])
    byte_length = value["byteLength"]
    if (
        isinstance(byte_length, bool)
        or not isinstance(byte_length, int)
        or not 1 <= byte_length <= MAX_ORIGINAL_BYTES
    ):
        raise MobileMediaValidationError("byteLength is outside the v1 limit.")
    original_mime_type = value["originalMimeType"]
    if (
        not isinstance(original_mime_type, str)
        or original_mime_type not in SUPPORTED_IMAGE_MIME_TYPES
    ):
        raise MobileMediaValidationError("originalMimeType is unsupported.")

    publication = _publication(
        value["publication"],
        path_upload_id,
        client_asset_id,
        byte_length,
        checksum,
    )
    provisional = MobileMediaCommit(
        event_id=_canonical_uuid(value["eventId"], "eventId"),
        upload_id=path_upload_id,
        client_asset_id=client_asset_id,
        owner_user_iri=_absolute_iri(value["ownerUserIri"], "ownerUserIri"),
        staging_area_id=_absolute_iri(value["stagingAreaId"], "stagingAreaId"),
        original_name=_original_name(value["originalName"]),
        original_mime_type=original_mime_type,
        byte_length=byte_length,
        checksum=checksum,
        comment=_comment(value.get("comment")),
        publication=publication,
        request_digest="",
    )
    try:
        canonical = rfc8785.dumps(provisional.canonical_payload())
    except (rfc8785.CanonicalizationError, TypeError) as error:
        raise MobileMediaValidationError(
            "The mobile-media commit cannot be canonicalized."
        ) from error
    return replace(provisional, request_digest=hashlib.sha256(canonical).hexdigest())


def _publication(
    value: Any,
    upload_id: str,
    client_asset_id: str,
    byte_length: int,
    checksum: str,
) -> PublicationEvidence:
    required = {
        "ownerUploadId",
        "assetId",
        "byteLength",
        "checksum",
        "derivativeNames",
        "storagePath",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise MobileMediaValidationError("publication evidence is invalid.")
    derivatives = value["derivativeNames"]
    if not isinstance(derivatives, list) or tuple(derivatives) != EXPECTED_DERIVATIVES:
        raise MobileMediaValidationError("publication derivatives are incomplete.")
    publication_byte_length = value["byteLength"]
    if (
        _canonical_uuid(value["ownerUploadId"], "publication.ownerUploadId")
        != upload_id
        or _canonical_uuid(value["assetId"], "publication.assetId") != client_asset_id
        or isinstance(publication_byte_length, bool)
        or not isinstance(publication_byte_length, int)
        or publication_byte_length != byte_length
        or _checksum(value["checksum"]) != checksum
    ):
        raise MobileMediaValidationError(
            "publication evidence does not match the commit."
        )
    try:
        storage_path = validated_relative_storage_path(value["storagePath"])
    except ValueError as error:
        raise MobileMediaValidationError(
            "publication storagePath is invalid."
        ) from error
    return PublicationEvidence(
        upload_id,
        client_asset_id,
        byte_length,
        checksum,
        EXPECTED_DERIVATIVES,
        storage_path,
    )


def _canonical_uuid(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise MobileMediaValidationError(f"{label} must be a canonical UUID.")
    try:
        parsed = UUID(value)
    except (ValueError, TypeError, AttributeError) as error:
        raise MobileMediaValidationError(
            f"{label} must be a canonical UUID."
        ) from error
    canonical = str(parsed)
    if value != canonical or parsed.int == 0:
        raise MobileMediaValidationError(f"{label} must be a canonical UUID.")
    return canonical


def _absolute_iri(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or not _is_valid_unicode(value)
        or value != value.strip()
        or any(character.isspace() or ord(character) < 32 for character in value)
        or any(character in '<>"{}|\\^`' for character in value)
    ):
        raise MobileMediaValidationError(f"{label} must be an absolute IRI.")
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        raise MobileMediaValidationError(f"{label} must be an absolute IRI.") from error
    if parsed.scheme not in {"http", "https", "urn"}:
        raise MobileMediaValidationError(f"{label} must be an absolute IRI.")
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise MobileMediaValidationError(f"{label} must be an absolute IRI.")
    if parsed.scheme == "urn" and not parsed.path:
        raise MobileMediaValidationError(f"{label} must be an absolute IRI.")
    return value


def _checksum(value: Any) -> str:
    if not isinstance(value, str) or CHECKSUM_RE.fullmatch(value) is None:
        raise MobileMediaValidationError("checksum must be a lower-case sha256 digest.")
    return value


def _original_name(value: Any) -> str:
    if not isinstance(value, str):
        raise MobileMediaValidationError("originalName must be a string.")
    normalized = unicodedata.normalize("NFC", value)
    if (
        not normalized
        or not _is_valid_unicode(normalized)
        or normalized in {".", ".."}
        or normalized != normalized.strip()
        or "/" in normalized
        or "\\" in normalized
        or any(ord(character) < 32 or ord(character) == 127 for character in normalized)
        or len(normalized.encode("utf-8")) > MAX_ORIGINAL_NAME_BYTES
    ):
        raise MobileMediaValidationError("originalName is not a safe path-free name.")
    return normalized


def _comment(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MobileMediaValidationError("comment must be a string.")
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized:
        return None
    if (
        not _is_valid_unicode(normalized)
        or len(normalized) > MAX_COMMENT_CHARACTERS
        or "\x00" in normalized
    ):
        raise MobileMediaValidationError("comment is outside the v1 limit.")
    return normalized


def validated_relative_storage_path(value: Any) -> str:
    """Return one exact portable relative path without silent normalization."""

    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or not _is_valid_unicode(value)
        or value.startswith("/")
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError("Storage path must be an exact safe relative path.")
    return value


def _is_valid_unicode(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True
