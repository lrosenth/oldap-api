"""Purpose-specific short-lived JWTs for direct SIP upload."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from .domain import ImportJob, MAX_COMPRESSED_BYTES

UPLOAD_TOKEN_TYPE = "ingest-upload"
UPLOAD_TOKEN_AUDIENCE = "oldap-media-ingest"
UPLOAD_TOKEN_TTL_SECONDS = 10 * 60


@dataclass(frozen=True, slots=True)
class UploadAuthorization:
    """One direct-upload request description returned only to the job owner."""

    url: str
    bearer_token: str
    expires_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "method": "PUT",
            "contentType": "application/zip",
            "bearerToken": self.bearer_token,
            "expiresAt": self.expires_at.isoformat().replace("+00:00", "Z"),
            "maxBytes": MAX_COMPRESSED_BYTES,
        }


class UploadCapabilityIssuer:
    """Issue audience-bound capabilities using a dedicated signing key."""

    def __init__(
        self,
        *,
        secret: str | None = None,
        media_ingest_base_url: str | None = None,
        issuer: str | None = None,
        ttl_seconds: int = UPLOAD_TOKEN_TTL_SECONDS,
    ) -> None:
        self._secret = secret or os.getenv("OLDAP_IMPORT_UPLOAD_JWT_SECRET", "")
        self._base_url = (
            media_ingest_base_url
            or os.getenv("OLDAP_MEDIA_INGEST_URL", "https://media.oldap.org")
        ).rstrip("/")
        self._issuer = issuer or os.getenv("OLDAP_JWT_ISSUER", "https://oldap.org")
        self._ttl_seconds = ttl_seconds

    def issue(
        self, job: ImportJob, *, now: datetime | None = None
    ) -> UploadAuthorization:
        """Create one token without persisting the bearer credential."""
        if len(self._secret.encode("utf-8")) < 32:
            raise RuntimeError(
                "OLDAP_IMPORT_UPLOAD_JWT_SECRET must contain at least 32 bytes."
            )
        other_secrets = {
            os.getenv("OLDAP_ACCESS_JWT_SECRET"),
            os.getenv("OLDAP_REFRESH_JWT_SECRET"),
            os.getenv("OLDAP_MEDIA_JWT_SECRET"),
            os.getenv("OLDAP_PASSWORD_RESET_JWT_SECRET"),
        }
        if self._secret in {value for value in other_secrets if value}:
            raise RuntimeError(
                "OLDAP_IMPORT_UPLOAD_JWT_SECRET must differ from all other JWT secrets."
            )
        current = now or datetime.now(UTC)
        expires_at = current + timedelta(seconds=self._ttl_seconds)
        payload = {
            "typ": UPLOAD_TOKEN_TYPE,
            "sub": job.requested_by_iri,
            "importId": job.import_id,
            "jti": str(uuid4()),
            "iat": current,
            "exp": expires_at,
            "iss": self._issuer,
            "aud": UPLOAD_TOKEN_AUDIENCE,
            "maxBytes": MAX_COMPRESSED_BYTES,
        }
        token = jwt.encode(payload, self._secret, algorithm="HS256")
        return UploadAuthorization(
            url=f"{self._base_url}/imports/{job.import_id}/sip",
            bearer_token=token,
            expires_at=expires_at,
        )
