"""Checksum and credential-boundary tests for retained import reports."""

import hashlib
import json
from datetime import UTC, datetime

import jwt
import pytest

from oldap_api.imports.domain import ImportJob, ImportState, TargetSnapshot
from oldap_api.imports.records import (
    RECORDS_TOKEN_AUDIENCE,
    ImportRecordClient,
    ImportRecordUnavailableError,
)

SECRET = "records-test-secret-at-least-thirty-two-bytes"


def _job(content: bytes) -> ImportJob:
    current = datetime.now(UTC)
    return ImportJob(
        import_id="11111111-1111-4111-8111-111111111111",
        state=ImportState.READY,
        state_version=3,
        created_at=current,
        updated_at=current,
        requested_by_iri="https://example.org/users/alice",
        requested_by_user_id="alice",
        target=TargetSnapshot(
            project_short_name="fasnacht",
            staging_area_iri="https://example.org/staging/area",
            staging_area_name="Area",
            target_root_folder_iri="https://example.org/staging/root",
            target_root_folder_name="Root",
        ),
        original_file_name="archive.zip",
        declared_compressed_size_bytes=1_000_000,
        quota_reserved_bytes=10_000_000,
        report_available=True,
        report_sha256=hashlib.sha256(content).hexdigest(),
    )


class FakeResponse:
    status_code = 200

    def __init__(self, content: bytes) -> None:
        self.content = content

    def json(self):
        return json.loads(self.content)


class FakeSession:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.headers = None
        self.url = None

    def get(self, url, *, headers, timeout):
        assert url.endswith(
            "/internal/imports/11111111-1111-4111-8111-111111111111/records/report"
        )
        assert timeout == (3.05, 15)
        self.url = url
        self.headers = headers
        return FakeResponse(self.content)


def _ready_report() -> bytes:
    """Return one canonical report body accepted by the record client."""
    return json.dumps(
        {
            "documentType": "oldap.zip-import.report",
            "schemaVersion": "1.0.0",
            "importId": "11111111-1111-4111-8111-111111111111",
            "status": "READY",
        },
        separators=(",", ":"),
    ).encode()


def test_report_bytes_are_verified_and_records_token_is_purpose_specific():
    content = _ready_report()
    session = FakeSession(content)
    client = ImportRecordClient(
        base_url="https://media.example.org",
        secret=SECRET,
        issuer="https://api.example.org",
        session=session,
    )

    report = client.get_report(_job(content))

    assert report["status"] == "READY"
    token = session.headers["Authorization"].removeprefix("Bearer ")
    claims = jwt.decode(
        token,
        SECRET,
        algorithms=["HS256"],
        audience=RECORDS_TOKEN_AUDIENCE,
        issuer="https://api.example.org",
    )
    assert claims["typ"] == "import-records"
    assert claims["importId"] == "11111111-1111-4111-8111-111111111111"


def test_internal_media_url_is_used_for_server_to_server_report_fetch(monkeypatch):
    content = _ready_report()
    session = FakeSession(content)
    monkeypatch.setenv("OLDAP_MEDIA_INGEST_URL", "https://media.home.org")
    monkeypatch.setenv("OLDAP_MEDIA_INTERNAL_URL", "http://media.home.org")

    ImportRecordClient(secret=SECRET, session=session).get_report(_job(content))

    assert session.url.startswith("http://media.home.org/internal/imports/")


def test_public_media_url_remains_the_compatible_internal_fallback(monkeypatch):
    content = _ready_report()
    session = FakeSession(content)
    monkeypatch.setenv("OLDAP_MEDIA_INGEST_URL", "https://media.oldap.org")
    monkeypatch.delenv("OLDAP_MEDIA_INTERNAL_URL", raising=False)

    ImportRecordClient(secret=SECRET, session=session).get_report(_job(content))

    assert session.url.startswith("https://media.oldap.org/internal/imports/")


def test_report_checksum_mismatch_is_never_proxied():
    expected = b'{"importId":"11111111-1111-4111-8111-111111111111"}'
    tampered = b'{"importId":"11111111-1111-4111-8111-111111111111","x":1}'
    client = ImportRecordClient(
        base_url="https://media.example.org",
        secret=SECRET,
        session=FakeSession(tampered),
    )

    with pytest.raises(ImportRecordUnavailableError):
        client.get_report(_job(expected))
