"""Purpose-specific API-to-media export source resolver tests."""

import jwt
import pytest

from oldap_api.exports.media_sources import (
    EXPORT_SOURCE_AUDIENCE,
    ExportSourceUnavailableError,
    MediaBinarySourceResolver,
)
from oldap_api.exports.staging_snapshot import LocalBinaryReference

SECRET = "export-source-service-secret-at-least-32-bytes"
MEDIA_IRI = "urn:uuid:11111111-1111-4111-8111-111111111111"


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def reference() -> LocalBinaryReference:
    return LocalBinaryReference(
        media_iri=MEDIA_IRI,
        asset_id="asset-one",
        storage_path_candidate="museum/image",
        original_name="One.jpg",
    )


def response_item() -> dict:
    return {
        "mediaIri": MEDIA_IRI,
        "assetId": "asset-one",
        "storagePath": "museum/image/asset-one/original/One.jpg",
        "originalName": "One.jpg",
        "originalMimeType": "image/jpeg",
        "sizeBytes": 12_345,
        "sha256": "a" * 64,
    }


def test_resolver_uses_exact_internal_route_and_purpose_specific_token():
    session = FakeSession(FakeResponse({"items": [response_item()]}))
    resolver = MediaBinarySourceResolver(
        secret=SECRET,
        media_internal_url="http://media.internal",
        issuer="https://oldap.example.org",
        session=session,
    )

    result = resolver.resolve((reference(),))

    assert result[MEDIA_IRI].size_bytes == 12_345
    url, request = session.calls[0]
    assert url == "http://media.internal/internal/export-sources/resolve"
    assert request["json"] == {
        "items": [
            {
                "mediaIri": MEDIA_IRI,
                "assetId": "asset-one",
                "storagePathCandidate": "museum/image",
                "originalName": "One.jpg",
            }
        ]
    }
    token = request["headers"]["Authorization"].removeprefix("Bearer ")
    claims = jwt.decode(
        token,
        SECRET,
        algorithms=["HS256"],
        audience=EXPORT_SOURCE_AUDIENCE,
        issuer="https://oldap.example.org",
    )
    assert claims["typ"] == "export-source-resolver"
    assert claims["sub"] == "oldap-api"


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse({"items": []}),
        FakeResponse({"items": [response_item() | {"sha256": "BAD"}]}),
        FakeResponse(
            {
                "items": [
                    {
                        key: value
                        for key, value in response_item().items()
                        if key != "sha256"
                    }
                ]
            }
        ),
        FakeResponse({"items": [response_item()]}, status_code=404),
        FakeResponse({"unexpected": []}),
    ],
)
def test_resolver_fails_closed_on_incomplete_invalid_or_failed_response(response):
    resolver = MediaBinarySourceResolver(
        secret=SECRET,
        session=FakeSession(response),
    )

    with pytest.raises(ExportSourceUnavailableError):
        resolver.resolve((reference(),))


def test_resolver_rejects_duplicate_request_identity_and_reused_secret(monkeypatch):
    resolver = MediaBinarySourceResolver(
        secret=SECRET,
        session=FakeSession(FakeResponse({"items": [response_item()]})),
    )
    with pytest.raises(ExportSourceUnavailableError, match="Duplicate"):
        resolver.resolve((reference(), reference()))

    monkeypatch.setenv("OLDAP_MEDIA_JWT_SECRET", SECRET)
    with pytest.raises(RuntimeError, match="purpose-specific"):
        MediaBinarySourceResolver(secret=SECRET)
