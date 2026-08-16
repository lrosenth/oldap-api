"""Purpose-specific short-lived download capabilities for ready ZIP exports."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import uuid4

import jwt

from .domain import ExportJob

DOWNLOAD_TOKEN_TYPE = "export-download"
DOWNLOAD_TOKEN_AUDIENCE = "oldap-media-export-download"
DOWNLOAD_TOKEN_TTL_SECONDS = 5 * 60


@dataclass(frozen=True, slots=True)
class ExportDownloadAuthorization:
    """Ephemeral direct-download description returned only to the job owner."""

    url: str
    expires_at: datetime

    def to_dict(self) -> dict[str, str]:
        """Return the browser-facing no-store contract."""

        return {
            "url": self.url,
            "method": "GET",
            "expiresAt": self.expires_at.isoformat().replace("+00:00", "Z"),
        }


class ExportDownloadCapabilityIssuer:
    """Issue exact-export capabilities using a dedicated signing key."""

    def __init__(
        self,
        *,
        secret: str | None = None,
        media_export_base_url: str | None = None,
        issuer: str | None = None,
        ttl_seconds: int = DOWNLOAD_TOKEN_TTL_SECONDS,
    ) -> None:
        self._secret = secret or os.getenv("OLDAP_EXPORT_DOWNLOAD_JWT_SECRET", "")
        self._base_url = (
            media_export_base_url
            if media_export_base_url is not None
            else os.getenv("OLDAP_MEDIA_EXPORT_URL", "")
        ).rstrip("/")
        self._issuer = issuer or os.getenv("OLDAP_JWT_ISSUER", "https://oldap.org")
        self._ttl_seconds = ttl_seconds

    def issue(
        self, job: ExportJob, *, now: datetime | None = None
    ) -> ExportDownloadAuthorization:
        """Issue one capability after verifying current artifact availability."""

        current = now or datetime.now(UTC)
        if not job.can_download(now=current):
            raise ValueError("Export artifact is not downloadable.")
        if len(self._secret.encode("utf-8")) < 32:
            raise RuntimeError(
                "OLDAP_EXPORT_DOWNLOAD_JWT_SECRET must contain at least 32 bytes."
            )
        other_names = (
            "OLDAP_ACCESS_JWT_SECRET",
            "OLDAP_REFRESH_JWT_SECRET",
            "OLDAP_MEDIA_JWT_SECRET",
            "OLDAP_IMPORT_UPLOAD_JWT_SECRET",
            "OLDAP_IMPORT_SERVICE_JWT_SECRET",
            "OLDAP_IMPORT_RECORDS_JWT_SECRET",
            "OLDAP_EXPORT_SERVICE_JWT_SECRET",
        )
        if self._secret in {
            value for name in other_names if (value := os.getenv(name, ""))
        }:
            raise RuntimeError(
                "OLDAP_EXPORT_DOWNLOAD_JWT_SECRET must be purpose-specific."
            )
        parsed_base_url = urlsplit(self._base_url)
        if (
            parsed_base_url.scheme not in {"http", "https"}
            or not parsed_base_url.netloc
            or parsed_base_url.path not in {"", "/"}
            or parsed_base_url.query
            or parsed_base_url.fragment
        ):
            raise RuntimeError(
                "OLDAP_MEDIA_EXPORT_URL must be an absolute HTTP(S) origin."
            )
        job_expiry = job.expires_at
        if job_expiry is None:  # Defensive type narrowing after can_download().
            raise ValueError("Export artifact has no expiry.")
        expires_at = min(current + timedelta(seconds=self._ttl_seconds), job_expiry)
        payload = {
            "typ": DOWNLOAD_TOKEN_TYPE,
            "sub": job.requested_by_iri,
            "exportId": job.export_id,
            "jti": str(uuid4()),
            "iat": current,
            "exp": expires_at,
            "iss": self._issuer,
            "aud": DOWNLOAD_TOKEN_AUDIENCE,
        }
        token = jwt.encode(payload, self._secret, algorithm="HS256")
        return ExportDownloadAuthorization(
            url=f"{self._base_url}/exports/{job.export_id}/archive?token={token}",
            expires_at=expires_at,
        )
