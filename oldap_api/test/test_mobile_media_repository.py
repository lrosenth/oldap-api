"""Atomic GraphDB mobile-media transaction and replay tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from oldap_api.mobile_media.domain import (
    MobileMediaCommitConflict,
    MobileMediaDestinationChangedError,
    MobileMediaInboxNotFoundError,
    MobileMediaInboxNotProtectedError,
    MobileMediaPermissionDeniedError,
    MobileMediaServiceUnavailableError,
    MobileMediaUploadPermissionDeniedError,
    validate_mobile_media_commit,
)
from oldap_api.mobile_media.repository import GraphDbMobileMediaRepository
from oldap_api.test.test_mobile_media_domain import (
    CHECKSUM,
    CLIENT_ASSET_ID,
    EVENT_ID,
    UPLOAD_ID,
    commit_request,
)

COMMITTED_AT = datetime(2026, 8, 20, 16, 0, tzinfo=UTC)
OWNER = "https://example.org/users/mobile-owner"
AREA = "urn:uuid:e1c03947-4f53-465f-85c5-0296e12bd0cc"
DEFAULT_ROLE = "urn:uuid:7866b8c8-83fa-49fa-9f75-ff4d650cd36e"
MOBILE = "urn:uuid:11111111-1111-4111-8111-111111111111"


def _bindings(rows: list[dict]) -> dict:
    return {"results": {"bindings": rows}}


def _value(value: str) -> dict[str, str]:
    return {"value": value}


class CommitConnection:
    """Script transaction queries while retaining the atomic update."""

    def __init__(
        self,
        *,
        receipt_rows: list[dict] | None = None,
        target_rows: list[dict] | None = None,
        admin_create: object = True,
        inbox_rows: list[dict] | None = None,
        collision: bool = False,
        update_error: Exception | None = None,
    ) -> None:
        self.receipt_rows = receipt_rows or []
        self.target_rows = (
            target_rows
            if target_rows is not None
            else [
                {
                    "dataGraph": _value("http://oldap.org/fasnacht#data"),
                    "project": _value("http://oldap.org/fasnacht"),
                    "projectShortName": _value("fasnacht"),
                    "defaultRole": _value(DEFAULT_ROLE),
                    "mediaPath": _value("bmg"),
                }
            ]
        )
        self.admin_create = admin_create
        self.inbox_rows = (
            inbox_rows
            if inbox_rows is not None
            else [
                {
                    "top": _value("urn:uuid:22222222-2222-4222-8222-222222222222"),
                    "mobile": _value(MOBILE),
                    "mobileRole": _value(DEFAULT_ROLE),
                    "mobilePermission": _value("http://oldap.org/base#DATA_VIEW"),
                }
            ]
        )
        self.collision = collision
        self.update_error = update_error
        self.queries: list[str] = []
        self.updates: list[str] = []
        self.started = 0
        self.committed = 0
        self.aborted = 0

    def transaction_start(self) -> None:
        self.started += 1

    def transaction_query(self, query: str):
        self.queries.append(query)
        if "mobile-media:result" in query:
            return _bindings(self.receipt_rows)
        if "SELECT ?dataGraph" in query:
            return _bindings(self.target_rows)
        if "ADMIN_CREATE" in query:
            return {"boolean": self.admin_create}
        if "SELECT ?top" in query:
            return _bindings(self.inbox_rows)
        if "shared:assetId" in query:
            return {"boolean": self.collision}
        raise AssertionError(f"Unexpected query: {query}")

    def transaction_update(self, update: str) -> None:
        self.updates.append(update)
        if self.update_error is not None:
            raise self.update_error

    def transaction_commit(self) -> None:
        self.committed += 1

    def transaction_abort(self) -> None:
        self.aborted += 1


def _commit():
    return validate_mobile_media_commit(UPLOAD_ID, commit_request())


def _receipt_row(commit, result) -> dict:
    return {
        "receipt": _value(commit.receipt_iri),
        "eventId": _value(commit.event_id),
        "requestDigest": _value(commit.request_digest),
        "owner": _value(commit.owner_user_iri),
        "stagingArea": _value(commit.staging_area_id),
        "resource": _value(commit.resource_iri),
        "result": _value(json.dumps(result.to_dict())),
    }


def test_resource_and_permanent_receipt_share_one_transaction() -> None:
    connection = CommitConnection()
    repository = GraphDbMobileMediaRepository(
        connection, media_ingest_base_url="https://media.example.org"
    )

    result = repository.commit(_commit(), committed_at=COMMITTED_AT)

    assert connection.started == 1
    assert connection.committed == 1
    assert connection.aborted == 0
    assert len(connection.updates) == 1
    update = connection.updates[0]
    assert "GRAPH <http://oldap.org/fasnacht#data>" in update
    assert "GRAPH <urn:oldap:mobile-media-commits>" in update
    assert "shared:StagingMediaObject" in update
    assert f'shared:assetId "{CLIENT_ASSET_ID}"' in update
    assert f'shared:checksum "{"a" * 64}"' in update
    assert 'shared:path "fasnacht/image/bmg"' in update
    assert f"shared:inStagingArea <{AREA}>" in update
    assert f"shared:inStagingFolder <{MOBILE}>" in update
    assert "shared:StagingStatusNew" in update
    assert f"oldap:attachedToRole <{DEFAULT_ROLE}>" in update
    assert "oldap:hasDataPermission oldap:DATA_DELETE" in update
    assert (
        'shared:serverUrl "https://media.example.org/iiif/3/"'
        "^^<http://www.w3.org/2001/XMLSchema#anyURI>" in update
    )
    assert 'schema:comment "Kurze Notiz"@en' in update
    assert result.asset_id == CLIENT_ASSET_ID
    assert result.resource_iri == _commit().resource_iri

    target_query = next(
        query for query in connection.queries if "SELECT ?dataGraph" in query
    )
    assert "fasnacht:memberOfOrganisation" in target_query
    assert "fasnacht:depositingOrganisation" in target_query
    assert "oldap:isActive true" in target_query
    assert "oldap:hasRole ?defaultRole" in target_query
    inbox_query = next(query for query in connection.queries if "SELECT ?top" in query)
    assert "OPTIONAL {\n      ?mobile a shared:StagingFolder" in inbox_query


def test_exact_receipt_replay_returns_original_result_without_new_write() -> None:
    commit = _commit()
    result = GraphDbMobileMediaRepository(
        CommitConnection(), media_ingest_base_url="https://media.example.org"
    ).commit(commit, committed_at=COMMITTED_AT)
    receipt = _receipt_row(commit, result)
    connection = CommitConnection(receipt_rows=[receipt])

    replay = GraphDbMobileMediaRepository(connection).commit(
        commit, committed_at=datetime(2030, 1, 1, tzinfo=UTC)
    )

    assert replay == result
    assert connection.committed == 1
    assert connection.aborted == 0
    assert connection.updates == []
    assert len(connection.queries) == 1


def test_changed_event_or_payload_cannot_reuse_a_receipt() -> None:
    commit = _commit()
    accepted = GraphDbMobileMediaRepository(
        CommitConnection(), media_ingest_base_url="https://media.example.org"
    ).commit(commit, committed_at=COMMITTED_AT)
    receipt = _receipt_row(commit, accepted) | {"requestDigest": _value("f" * 64)}
    connection = CommitConnection(receipt_rows=[receipt])

    with pytest.raises(MobileMediaCommitConflict):
        GraphDbMobileMediaRepository(connection).commit(commit)
    assert connection.committed == 0
    assert connection.aborted == 1
    assert connection.updates == []


def test_corrupt_permanent_receipt_fails_closed_without_repairing_over_it() -> None:
    connection = CommitConnection(
        receipt_rows=[
            {
                "eventId": _value(EVENT_ID),
                "requestDigest": _value(_commit().request_digest),
            }
        ]
    )

    with pytest.raises(MobileMediaServiceUnavailableError):
        GraphDbMobileMediaRepository(connection).commit(_commit())

    assert connection.committed == 0
    assert connection.aborted == 1
    assert connection.updates == []


def test_receipt_with_wrong_identity_or_asset_mapping_fails_closed() -> None:
    commit = _commit()
    accepted = GraphDbMobileMediaRepository(
        CommitConnection(), media_ingest_base_url="https://media.example.org"
    ).commit(commit, committed_at=COMMITTED_AT)
    wrong_result = accepted.to_dict() | {
        "assetId": "99999999-9999-4999-8999-999999999999"
    }

    for receipt in (
        _receipt_row(commit, accepted)
        | {"receipt": _value("urn:oldap:mobile-media-commit:foreign")},
        _receipt_row(commit, accepted) | {"result": _value(json.dumps(wrong_result))},
        _receipt_row(commit, accepted)
        | {"owner": _value("https://example.org/users/foreign")},
    ):
        connection = CommitConnection(receipt_rows=[receipt])
        with pytest.raises(MobileMediaCommitConflict):
            GraphDbMobileMediaRepository(connection).commit(commit)
        assert connection.aborted == 1
        assert connection.updates == []


def test_event_identity_cannot_be_reused_for_another_upload_or_asset() -> None:
    accepted_commit = _commit()
    accepted = GraphDbMobileMediaRepository(
        CommitConnection(), media_ingest_base_url="https://media.example.org"
    ).commit(accepted_commit, committed_at=COMMITTED_AT)
    value = commit_request()
    value["uploadId"] = "11111111-1111-4111-8111-111111111111"
    value["clientAssetId"] = "22222222-2222-4222-8222-222222222222"
    value["publication"]["ownerUploadId"] = value["uploadId"]
    value["publication"]["assetId"] = value["clientAssetId"]
    conflicting = validate_mobile_media_commit(value["uploadId"], value)
    connection = CommitConnection(
        receipt_rows=[_receipt_row(accepted_commit, accepted)]
    )

    with pytest.raises(MobileMediaCommitConflict):
        GraphDbMobileMediaRepository(connection).commit(conflicting)

    receipt_query = connection.queries[0]
    assert f'?eventId = "{EVENT_ID}"' in receipt_query
    assert connection.updates == []
    assert connection.aborted == 1


@pytest.mark.parametrize(
    "query_result",
    [{}, {"results": {}}, {"results": {"bindings": "not-a-list"}}],
)
def test_malformed_receipt_query_cannot_be_mistaken_for_an_absent_receipt(
    query_result,
) -> None:
    class MalformedConnection(CommitConnection):
        def transaction_query(self, query: str):
            if "mobile-media:result" in query:
                return query_result
            return super().transaction_query(query)

    connection = MalformedConnection()
    with pytest.raises(MobileMediaServiceUnavailableError):
        GraphDbMobileMediaRepository(connection).commit(_commit())
    assert connection.aborted == 1
    assert connection.updates == []


def test_non_boolean_ask_result_never_grants_permission() -> None:
    connection = CommitConnection(admin_create="false")

    with pytest.raises(MobileMediaServiceUnavailableError):
        GraphDbMobileMediaRepository(connection).commit(_commit())

    assert connection.aborted == 1
    assert connection.updates == []


@pytest.mark.parametrize(
    "media_url",
    [
        "https://",
        "ftp://media.example.org",
        "https://user:password@media.example.org",
        "https://media.example.org?token=secret",
        "https://media.example.org/#fragment",
    ],
)
def test_invalid_media_delivery_origins_fail_before_a_transaction(media_url) -> None:
    connection = CommitConnection()

    with pytest.raises(MobileMediaServiceUnavailableError):
        GraphDbMobileMediaRepository(connection, media_ingest_base_url=media_url)

    assert connection.started == 0


@pytest.mark.parametrize(
    "media_path",
    [
        "bmg//mobile",
        "bmg/./mobile",
        "bmg/../mobile",
        "/bmg",
        "bmg\\mobile",
        "bmg\nmobile",
    ],
)
def test_noncanonical_server_media_path_fails_closed(media_path) -> None:
    target = CommitConnection().target_rows[0] | {"mediaPath": _value(media_path)}
    connection = CommitConnection(target_rows=[target])

    with pytest.raises(MobileMediaServiceUnavailableError):
        GraphDbMobileMediaRepository(connection).commit(_commit())

    assert connection.aborted == 1
    assert connection.updates == []


def test_published_path_must_match_the_current_server_derived_path() -> None:
    value = commit_request()
    value["publication"]["storagePath"] = "fasnacht/image/previous-bmg"
    commit = validate_mobile_media_commit(UPLOAD_ID, value)
    connection = CommitConnection()

    with pytest.raises(MobileMediaDestinationChangedError):
        GraphDbMobileMediaRepository(connection).commit(commit)

    assert connection.aborted == 1
    assert connection.updates == []


def test_missing_mobile_under_one_root_is_not_mistaken_for_a_valid_inbox() -> None:
    connection = CommitConnection(
        inbox_rows=[{"top": _value("urn:uuid:22222222-2222-4222-8222-222222222222")}]
    )

    with pytest.raises(MobileMediaInboxNotFoundError):
        GraphDbMobileMediaRepository(connection).commit(_commit())

    assert connection.aborted == 1
    assert connection.updates == []


def test_second_exact_root_without_mobile_makes_the_inbox_ambiguous() -> None:
    complete = CommitConnection().inbox_rows[0]
    connection = CommitConnection(
        inbox_rows=[
            complete,
            {"top": _value("urn:uuid:33333333-3333-4333-8333-333333333333")},
        ]
    )

    with pytest.raises(MobileMediaInboxNotProtectedError):
        GraphDbMobileMediaRepository(connection).commit(_commit())

    assert connection.aborted == 1
    assert connection.updates == []


@pytest.mark.parametrize(
    ("connection", "error"),
    [
        (CommitConnection(target_rows=[]), MobileMediaPermissionDeniedError),
        (
            CommitConnection(admin_create=False),
            MobileMediaUploadPermissionDeniedError,
        ),
        (CommitConnection(inbox_rows=[]), MobileMediaInboxNotFoundError),
        (
            CommitConnection(
                inbox_rows=[
                    {
                        "top": _value("urn:uuid:22222222-2222-4222-8222-222222222222"),
                        "mobile": _value(MOBILE),
                        "mobileRole": _value(DEFAULT_ROLE),
                        "mobilePermission": _value("http://oldap.org/base#DATA_UPDATE"),
                    }
                ]
            ),
            MobileMediaInboxNotProtectedError,
        ),
        (CommitConnection(collision=True), MobileMediaCommitConflict),
    ],
)
def test_live_authorization_and_collision_failures_abort_without_writes(
    connection, error
) -> None:
    with pytest.raises(error):
        GraphDbMobileMediaRepository(connection).commit(_commit())
    assert connection.committed == 0
    assert connection.aborted == 1
    assert connection.updates == []


def test_failed_atomic_insert_aborts_and_never_commits() -> None:
    connection = CommitConnection(update_error=RuntimeError("GraphDB write failed"))

    with pytest.raises(RuntimeError, match="GraphDB write failed"):
        GraphDbMobileMediaRepository(connection).commit(_commit())

    assert connection.committed == 0
    assert connection.aborted == 1
    assert len(connection.updates) == 1
