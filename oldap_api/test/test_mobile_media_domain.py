"""Closed mobile-media commit contract tests."""

from copy import deepcopy
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

from oldap_api.mobile_media.domain import (
    MAX_ORIGINAL_BYTES,
    MobileMediaValidationError,
    validate_mobile_media_commit,
)
from oldap_api.mobile_media.service import MobileMediaCommitService

UPLOAD_ID = "0a7520d7-00b8-4bec-9764-05b57baf9585"
EVENT_ID = str(uuid5(NAMESPACE_URL, f"mobile-media-event:{UPLOAD_ID}"))
CLIENT_ASSET_ID = "4d919878-4f17-473a-a02f-e091ce70bbb0"
CHECKSUM = f"sha256:{'a' * 64}"


def commit_request() -> dict:
    """Return one valid closed media-to-OLDAP request."""

    return {
        "eventId": EVENT_ID,
        "uploadId": UPLOAD_ID,
        "clientAssetId": CLIENT_ASSET_ID,
        "ownerUserIri": "https://example.org/users/mobile-owner",
        "stagingAreaId": "urn:uuid:e1c03947-4f53-465f-85c5-0296e12bd0cc",
        "originalName": "Fasnacht 2026.jpg",
        "originalMimeType": "image/jpeg",
        "byteLength": 1_234_567,
        "checksum": CHECKSUM,
        "comment": "Kurze Notiz",
        "publication": {
            "ownerUploadId": UPLOAD_ID,
            "assetId": CLIENT_ASSET_ID,
            "byteLength": 1_234_567,
            "checksum": CHECKSUM,
            "derivativeNames": ["master.tif"],
            "storagePath": "fasnacht/image/bmg",
        },
    }


def test_closed_commit_is_normalized_and_rfc8785_stable() -> None:
    request = commit_request()
    first = validate_mobile_media_commit(UPLOAD_ID, request)
    reordered = {key: request[key] for key in reversed(request)}
    second = validate_mobile_media_commit(UPLOAD_ID, reordered)

    assert first.request_digest == second.request_digest
    assert first.checksum_sha256 == "a" * 64
    assert first.comment == "Kurze Notiz"
    assert first.resource_iri == second.resource_iri
    assert first.resource_iri.startswith("urn:uuid:")
    assert first.receipt_iri == f"urn:oldap:mobile-media-commit:{CLIENT_ASSET_ID}"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update({"folderIri": "urn:uuid:forbidden"}), "fields"),
        (lambda value: value.update({"uploadId": str(uuid4())}), "route"),
        (lambda value: value.update({"originalName": "../escape.jpg"}), "path-free"),
        (
            lambda value: value.update({"ownerUserIri": "urn:user:bad value"}),
            "absolute IRI",
        ),
        (lambda value: value.update({"originalMimeType": "image/gif"}), "unsupported"),
        (lambda value: value.update({"originalMimeType": []}), "unsupported"),
        (lambda value: value.update({"byteLength": MAX_ORIGINAL_BYTES + 1}), "limit"),
        (lambda value: value.update({"checksum": f"sha256:{'A' * 64}"}), "digest"),
        (
            lambda value: value["publication"].update({"assetId": str(uuid4())}),
            "does not match",
        ),
        (
            lambda value: value["publication"].update({"byteLength": 42}),
            "does not match",
        ),
        (
            lambda value: (
                value.update({"byteLength": 1}),
                value["publication"].update({"byteLength": True}),
            ),
            "does not match",
        ),
        (
            lambda value: value["publication"].update({"derivativeNames": []}),
            "incomplete",
        ),
        (
            lambda value: value["publication"].update(
                {"storagePath": "fasnacht/image//bmg"}
            ),
            "storagePath",
        ),
        (
            lambda value: value.update({"ownerUserIri": "https://["}),
            "absolute IRI",
        ),
    ],
)
def test_commit_rejects_untrusted_or_inconsistent_fields(mutation, message) -> None:
    value = deepcopy(commit_request())
    mutation(value)

    with pytest.raises(MobileMediaValidationError, match=message):
        validate_mobile_media_commit(UPLOAD_ID, value)


def test_service_validates_before_repository_side_effects() -> None:
    class RecordingRepository:
        called = False

        def commit(self, commit, *, committed_at=None):
            self.called = True
            raise AssertionError("repository must not be called")

    class RecordingLock:
        called = False

        def run(self, operation):
            self.called = True
            return operation()

    repository = RecordingRepository()
    commit_lock = RecordingLock()
    service = MobileMediaCommitService(repository, commit_lock)

    with pytest.raises(MobileMediaValidationError):
        service.commit(UPLOAD_ID, {"unexpected": True})
    assert repository.called is False
    assert commit_lock.called is False


def test_invalid_unicode_filename_is_a_stable_validation_failure() -> None:
    value = commit_request()
    value["originalName"] = "invalid\ud800.jpg"

    with pytest.raises(MobileMediaValidationError, match="path-free"):
        validate_mobile_media_commit(UPLOAD_ID, value)
