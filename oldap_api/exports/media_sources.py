"""Purpose-specific oldap-api client for resolving export source originals."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import requests

from .snapshot_common import LocalBinaryReference, ResolvedBinarySource

EXPORT_SOURCE_TOKEN_TYPE = "export-source-resolver"
EXPORT_SOURCE_AUDIENCE = "oldap-media-export-service"
MAX_RESOLVE_BATCH = 1_000


class ExportSourceUnavailableError(RuntimeError):
    """Raised when media cannot authoritatively resolve one source batch."""


class MediaBinarySourceResolver:
    """Resolve original facts through the internal media-service boundary."""

    def __init__(
        self,
        *,
        secret: str | None = None,
        media_internal_url: str | None = None,
        issuer: str | None = None,
        subject: str = "oldap-api",
        timeout_seconds: float = 15.0,
        session: requests.Session | None = None,
    ) -> None:
        self._secret = secret or os.getenv("OLDAP_EXPORT_SERVICE_JWT_SECRET", "")
        if len(self._secret.encode("utf-8")) < 32:
            raise RuntimeError(
                "OLDAP_EXPORT_SERVICE_JWT_SECRET must contain at least 32 bytes."
            )
        _assert_purpose_specific_secret(self._secret)
        self._base_url = (
            media_internal_url
            or os.getenv("OLDAP_MEDIA_INTERNAL_URL")
            or os.getenv("OLDAP_MEDIA_INGEST_URL", "https://media.oldap.org")
        ).rstrip("/")
        self._issuer = issuer or os.getenv("OLDAP_JWT_ISSUER", "https://oldap.org")
        self._subject = subject
        self._timeout = timeout_seconds
        self._session = session or requests.Session()

    def resolve(
        self, references: tuple[LocalBinaryReference, ...]
    ) -> dict[str, ResolvedBinarySource]:
        """Resolve bounded batches and reject missing, duplicate, or extra results."""

        if len({item.media_iri for item in references}) != len(references):
            raise ExportSourceUnavailableError("Duplicate media IRI in source request.")
        result: dict[str, ResolvedBinarySource] = {}
        for offset in range(0, len(references), MAX_RESOLVE_BATCH):
            batch = references[offset : offset + MAX_RESOLVE_BATCH]
            try:
                response = self._session.post(
                    f"{self._base_url}/internal/export-sources/resolve",
                    json={"items": [_reference_dict(item) for item in batch]},
                    headers={
                        "Authorization": f"Bearer {self._token()}",
                        "Accept": "application/json",
                    },
                    timeout=self._timeout,
                )
            except requests.RequestException as error:
                raise ExportSourceUnavailableError(
                    "Media source resolver is unavailable."
                ) from error
            if response.status_code != 200:
                raise ExportSourceUnavailableError(
                    f"Media source resolver returned HTTP {response.status_code}."
                )
            try:
                payload = response.json()
            except ValueError as error:
                raise ExportSourceUnavailableError(
                    "Media source resolver returned invalid JSON."
                ) from error
            if not isinstance(payload, dict) or set(payload) != {"items"}:
                raise ExportSourceUnavailableError("Invalid media source response.")
            items = payload["items"]
            if not isinstance(items, list) or len(items) != len(batch):
                raise ExportSourceUnavailableError("Incomplete media source response.")
            for value in items:
                media_iri, source = _resolved_source(value)
                if media_iri in result:
                    raise ExportSourceUnavailableError(
                        "Duplicate media IRI in source response."
                    )
                result[media_iri] = source
            expected = {item.media_iri for item in batch}
            if set(result).intersection(expected) != expected:
                raise ExportSourceUnavailableError(
                    "Media source response does not match the requested batch."
                )
        if set(result) != {item.media_iri for item in references}:
            raise ExportSourceUnavailableError("Media source response contains extras.")
        return result

    def _token(self, *, now: datetime | None = None) -> str:
        current = now or datetime.now(UTC)
        return jwt.encode(
            {
                "typ": EXPORT_SOURCE_TOKEN_TYPE,
                "sub": self._subject,
                "iat": current,
                "exp": current + timedelta(minutes=1),
                "iss": self._issuer,
                "aud": EXPORT_SOURCE_AUDIENCE,
            },
            self._secret,
            algorithm="HS256",
        )


def _reference_dict(value: LocalBinaryReference) -> dict[str, str]:
    return {
        "mediaIri": value.media_iri,
        "assetId": value.asset_id,
        "storagePathCandidate": value.storage_path_candidate,
        "originalName": value.original_name,
    }


def _resolved_source(value: Any) -> tuple[str, ResolvedBinarySource]:
    required = {
        "mediaIri",
        "assetId",
        "storagePath",
        "originalName",
        "originalMimeType",
        "sizeBytes",
        "sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ExportSourceUnavailableError("Invalid resolved source item.")
    size = value["sizeBytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ExportSourceUnavailableError("Invalid resolved source size.")
    strings = {key: value[key] for key in required - {"sizeBytes"}}
    if any(not isinstance(item, str) or not item for item in strings.values()):
        raise ExportSourceUnavailableError("Invalid resolved source identity.")
    sha256 = value["sha256"]
    if (
        not isinstance(sha256, str)
        or len(sha256) != 64
        or any(character not in "0123456789abcdef" for character in sha256)
    ):
        raise ExportSourceUnavailableError("Invalid resolved source digest.")
    return str(value["mediaIri"]), ResolvedBinarySource(
        asset_id=str(value["assetId"]),
        storage_path=str(value["storagePath"]),
        original_name=str(value["originalName"]),
        original_mime_type=str(value["originalMimeType"]),
        size_bytes=size,
        sha256=sha256,
    )


def _assert_purpose_specific_secret(secret: str) -> None:
    other_names = (
        "OLDAP_ACCESS_JWT_SECRET",
        "OLDAP_REFRESH_JWT_SECRET",
        "OLDAP_MEDIA_JWT_SECRET",
        "OLDAP_IMPORT_SERVICE_JWT_SECRET",
        "OLDAP_IMPORT_UPLOAD_JWT_SECRET",
        "OLDAP_IMPORT_RECORDS_JWT_SECRET",
        "OLDAP_EXPORT_DOWNLOAD_JWT_SECRET",
    )
    if secret in {os.getenv(name) for name in other_names if os.getenv(name)}:
        raise RuntimeError("Export service JWT secret must be purpose-specific.")
