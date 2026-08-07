"""Authenticated API-to-media retrieval of immutable import records."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import requests

from .domain import ImportJob

RECORDS_TOKEN_TYPE = "import-records"
RECORDS_TOKEN_AUDIENCE = "oldap-media-import-records"
MAX_REPORT_RESPONSE_BYTES = 5_000_000


class ImportReportNotReadyError(RuntimeError):
    """Raised when no retained report is available for the job."""

    code = "IMPORT_REPORT_NOT_READY"


class ImportRecordUnavailableError(RuntimeError):
    """Raised when media records cannot be reached or verified."""

    code = "IMPORT_RECORD_UNAVAILABLE"


class ImportRecordClient:
    """Fetch retained JSON records without exposing the records token."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        secret: str | None = None,
        issuer: str | None = None,
        session: Any = requests,
    ) -> None:
        self._base_url = (
            base_url or os.getenv("OLDAP_MEDIA_INGEST_URL", "https://media.oldap.org")
        ).rstrip("/")
        self._secret = secret or os.getenv("OLDAP_IMPORT_RECORDS_JWT_SECRET", "")
        self._issuer = issuer or os.getenv("OLDAP_JWT_ISSUER", "https://oldap.org")
        self._session = session

    def get_report(self, job: ImportJob) -> dict[str, Any]:
        """Return and checksum-verify the exact retained report representation."""
        if not job.report_available or not job.report_sha256:
            raise ImportReportNotReadyError("The validation report is not available.")
        token = self._issue_token(job.import_id)
        try:
            response = self._session.get(
                f"{self._base_url}/internal/imports/{job.import_id}/records/report",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                timeout=(3.05, 15),
            )
        except requests.RequestException as error:
            raise ImportRecordUnavailableError(
                "The retained report service is unavailable."
            ) from error
        if response.status_code in {404, 409}:
            raise ImportReportNotReadyError("The validation report is not available.")
        if response.status_code != 200:
            raise ImportRecordUnavailableError(
                "The retained report service rejected the request."
            )
        content = response.content
        if len(content) > MAX_REPORT_RESPONSE_BYTES:
            raise ImportRecordUnavailableError(
                "The retained report exceeds the response limit."
            )
        if hashlib.sha256(content).hexdigest() != job.report_sha256:
            raise ImportRecordUnavailableError(
                "The retained report checksum does not match."
            )
        try:
            payload = response.json()
        except ValueError as error:
            raise ImportRecordUnavailableError(
                "The retained report is not valid JSON."
            ) from error
        if not isinstance(payload, dict) or payload.get("importId") != job.import_id:
            raise ImportRecordUnavailableError(
                "The retained report identity does not match."
            )
        if (
            job.validation_outcome
            and payload.get("status") != job.validation_outcome.value
        ):
            raise ImportRecordUnavailableError(
                "The retained report outcome does not match."
            )
        return payload

    def _issue_token(self, import_id: str) -> str:
        if len(self._secret.encode("utf-8")) < 32:
            raise ImportRecordUnavailableError(
                "OLDAP_IMPORT_RECORDS_JWT_SECRET must contain at least 32 bytes."
            )
        other = {
            os.getenv("OLDAP_ACCESS_JWT_SECRET"),
            os.getenv("OLDAP_REFRESH_JWT_SECRET"),
            os.getenv("OLDAP_MEDIA_JWT_SECRET"),
            os.getenv("OLDAP_PASSWORD_RESET_JWT_SECRET"),
            os.getenv("OLDAP_IMPORT_UPLOAD_JWT_SECRET"),
            os.getenv("OLDAP_IMPORT_SERVICE_JWT_SECRET"),
        }
        if self._secret in {value for value in other if value}:
            raise ImportRecordUnavailableError(
                "The import records JWT secret must be purpose-specific."
            )
        current = datetime.now(UTC)
        return jwt.encode(
            {
                "typ": RECORDS_TOKEN_TYPE,
                "sub": "oldap-api",
                "importId": import_id,
                "iat": current,
                "exp": current + timedelta(minutes=5),
                "iss": self._issuer,
                "aud": RECORDS_TOKEN_AUDIENCE,
            },
            self._secret,
            algorithm="HS256",
        )
