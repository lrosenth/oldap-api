"""Atomic outbox, lease replay, and purpose-authentication tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from flask import Flask

from oldap_api.mobile_media import internal_auth
from oldap_api.mobile_media.lifecycle import (
    GraphDbMobileMediaLifecycleOutbox,
    MobileMediaLifecycleError,
)
from oldap_api.views import mobile_media_lifecycle_views

EVENT = "11111111-1111-4111-8111-111111111111"
CLAIM = "22222222-2222-4222-8222-222222222222"
UPLOAD = "33333333-3333-4333-8333-333333333333"
ASSET = "44444444-4444-4444-8444-444444444444"
WORKER = "worker-1"
OWNER = "https://oldap.org/users/alice"
AREA = "urn:uuid:55555555-5555-4555-8555-555555555555"
RESOURCE = "urn:uuid:66666666-6666-4666-8666-666666666666"
CHECKSUM = "sha256:" + "a" * 64
NOW = datetime(2026, 9, 2, 12, tzinfo=UTC)


def _bindings(rows):
    return {"results": {"bindings": rows}}


def _value(value: str):
    return {"value": value}


def _uri(value: str):
    return {"type": "uri", "value": value}


def _any_uri(value: str):
    return {
        "type": "literal",
        "value": value,
        "datatype": "http://www.w3.org/2001/XMLSchema#anyURI",
    }


def _claim_row(state: str = "pending"):
    return {
        "event": _value(f"urn:oldap:mobile-media-lifecycle:{EVENT}"),
        "eventId": _value(EVENT),
        "kind": _value("staging_deleted"),
        "uploadId": _value(UPLOAD),
        "clientAssetId": _value(ASSET),
        "owner": _value(OWNER),
        "stagingArea": _value(AREA),
        "resource": _value(RESOURCE),
        "checksum": _value(CHECKSUM),
        "createdAt": _value("2026-09-02T12:00:00Z"),
        "state": _value(state),
    }


class Connection:
    def __init__(self, query_results):
        self.query_results = list(query_results)
        self.updates: list[str] = []
        self.started = 0
        self.committed = 0
        self.aborted = 0

    def transaction_start(self):
        self.started += 1

    def transaction_query(self, query: str):
        return self.query_results.pop(0)

    def transaction_update(self, update: str):
        self.updates.append(update)

    def transaction_commit(self):
        self.committed += 1

    def transaction_abort(self):
        self.aborted += 1


def test_outbox_append_joins_the_permanent_receipt_in_callers_transaction() -> None:
    connection = Connection([])
    outbox = GraphDbMobileMediaLifecycleOutbox(connection)

    outbox.append_to_active_transaction(
        event_id=EVENT,
        kind="staging_deleted",
        resource_iri=RESOURCE,
        checksum=CHECKSUM,
        occurred_at=NOW,
    )

    assert connection.started == connection.committed == connection.aborted == 0
    assert len(connection.updates) == 1
    update = connection.updates[0]
    assert "LifecycleEvent" in update
    assert "CommitReceipt" in update
    assert RESOURCE in update
    assert f'"{RESOURCE}"^^<http://www.w3.org/2001/XMLSchema#anyURI>' in update
    assert f"<urn:oldap:mobile-media:resource> <{RESOURCE}>" not in update
    assert '"staging_deleted"' in update


def test_legacy_resource_reference_is_normalized_without_weakening_in_use_guard() -> (
    None
):
    receipt = f"urn:oldap:mobile-media-commit:{ASSET}"
    connection = Connection(
        [_bindings([{"receipt": _uri(receipt), "resource": _uri(RESOURCE)}])]
    )

    normalized = GraphDbMobileMediaLifecycleOutbox(
        connection
    ).normalize_legacy_resource_reference(RESOURCE)

    assert normalized is True
    assert connection.started == connection.committed == 1
    assert connection.aborted == 0
    assert len(connection.updates) == 1
    update = connection.updates[0]
    assert f"<urn:oldap:mobile-media:resource> <{RESOURCE}>" in update
    assert f'"{RESOURCE}"^^<http://www.w3.org/2001/XMLSchema#anyURI>' in update
    assert "?subject" in update


def test_normalization_accepts_current_receipt_and_noops_for_legacy_media() -> None:
    receipt = f"urn:oldap:mobile-media-commit:{ASSET}"
    current = Connection(
        [_bindings([{"receipt": _uri(receipt), "resource": _any_uri(RESOURCE)}])]
    )
    missing = Connection([_bindings([])])

    assert (
        GraphDbMobileMediaLifecycleOutbox(current).normalize_legacy_resource_reference(
            RESOURCE
        )
        is True
    )
    assert current.committed == 1
    assert (
        GraphDbMobileMediaLifecycleOutbox(missing).normalize_legacy_resource_reference(
            RESOURCE
        )
        is False
    )
    assert missing.committed == 1
    assert missing.updates == []


def test_contradictory_or_malformed_receipt_aborts_normalization() -> None:
    receipt = f"urn:oldap:mobile-media-commit:{ASSET}"
    contradictory = Connection(
        [
            _bindings(
                [
                    {"receipt": _uri(receipt), "resource": _uri(RESOURCE)},
                    {
                        "receipt": _uri(
                            "urn:oldap:mobile-media-commit:77777777-7777-4777-8777-777777777777"
                        ),
                        "resource": _uri(RESOURCE),
                    },
                ]
            )
        ]
    )
    malformed = Connection(
        [
            _bindings(
                [
                    {
                        "receipt": _uri(receipt),
                        "resource": {"type": "literal", "value": RESOURCE},
                    }
                ]
            )
        ]
    )

    with pytest.raises(MobileMediaLifecycleError, match="contradictory"):
        GraphDbMobileMediaLifecycleOutbox(
            contradictory
        ).normalize_legacy_resource_reference(RESOURCE)
    with pytest.raises(MobileMediaLifecycleError, match="invalid"):
        GraphDbMobileMediaLifecycleOutbox(
            malformed
        ).normalize_legacy_resource_reference(RESOURCE)

    assert contradictory.aborted == 1
    assert malformed.aborted == 1


def test_claim_is_leased_transactionally_and_reclaimable_after_expiry(
    monkeypatch,
) -> None:
    connection = Connection([_bindings([_claim_row()])])
    monkeypatch.setattr("oldap_api.mobile_media.lifecycle.uuid4", lambda: CLAIM)

    claim = GraphDbMobileMediaLifecycleOutbox(connection, lease_seconds=30).claim_next(
        WORKER, now=NOW
    )

    assert claim is not None
    assert claim.event_id == EVENT
    assert claim.claim_id == CLAIM
    assert claim.lease_expires_at == NOW + timedelta(seconds=30)
    assert connection.started == connection.committed == 1
    assert connection.aborted == 0
    assert '"claimed"' in connection.updates[0]


def test_completion_rejects_a_stale_claim_and_replays_delivered_state() -> None:
    stale = Connection(
        [
            _bindings(
                [
                    {
                        "state": _value("claimed"),
                        "claimId": _value(CLAIM),
                        "workerId": _value("other"),
                    }
                ]
            )
        ]
    )
    with pytest.raises(MobileMediaLifecycleError):
        GraphDbMobileMediaLifecycleOutbox(stale).complete(
            EVENT, CLAIM, WORKER, completed_at=NOW
        )
    assert stale.aborted == 1

    completed = Connection(
        [
            _bindings(
                [
                    {
                        "state": _value("claimed"),
                        "claimId": _value(CLAIM),
                        "workerId": _value(WORKER),
                    }
                ]
            )
        ]
    )
    GraphDbMobileMediaLifecycleOutbox(completed).complete(
        EVENT, CLAIM, WORKER, completed_at=NOW
    )
    assert completed.committed == 1
    assert len(completed.updates) == 1
    assert '"delivered"' in completed.updates[0]
    assert completed.updates[0].count(f'"{CLAIM}"') == 1
    assert completed.updates[0].count(f'"{WORKER}"') == 1

    delivered = Connection(
        [
            _bindings(
                [
                    {
                        "state": _value("delivered"),
                        "claimId": _value(CLAIM),
                        "workerId": _value(WORKER),
                    }
                ]
            )
        ]
    )
    GraphDbMobileMediaLifecycleOutbox(delivered).complete(
        EVENT, CLAIM, WORKER, completed_at=NOW
    )
    assert delivered.committed == 1
    assert delivered.updates == []

    late_stale = Connection(
        [
            _bindings(
                [
                    {
                        "state": _value("delivered"),
                        "claimId": _value(CLAIM),
                        "workerId": _value("other-worker"),
                    }
                ]
            )
        ]
    )
    with pytest.raises(MobileMediaLifecycleError, match="claim is stale"):
        GraphDbMobileMediaLifecycleOutbox(late_stale).complete(
            EVENT, CLAIM, WORKER, completed_at=NOW
        )
    assert late_stale.aborted == 1


def _token(secret: str, *, purpose: str, audience: str) -> str:
    issued_at = datetime.now(UTC)
    return jwt.encode(
        {
            "typ": internal_auth.MOBILE_MEDIA_TOKEN_TYPE,
            "purpose": purpose,
            "sub": internal_auth.MOBILE_MEDIA_SUBJECT,
            "aud": audience,
            "iss": "https://oldap.org",
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(seconds=120)).timestamp()),
        },
        secret,
        algorithm="HS256",
    )


def test_commit_token_cannot_claim_lifecycle_work(monkeypatch) -> None:
    secret = "s" * 64
    monkeypatch.setenv("OLDAP_MOBILE_MEDIA_SERVICE_JWT_SECRET", secret)
    app = Flask(__name__)
    app.register_blueprint(
        mobile_media_lifecycle_views.internal_mobile_media_lifecycle_bp
    )
    client = app.test_client()
    commit_token = _token(
        secret,
        purpose=internal_auth.MOBILE_MEDIA_TOKEN_PURPOSE,
        audience=internal_auth.MOBILE_MEDIA_AUDIENCE,
    )

    response = client.post(
        "/internal/mobile-media/v1/lifecycle-events/claims",
        json={"workerId": WORKER},
        headers={"Authorization": f"Bearer {commit_token}"},
    )

    assert response.status_code == 401
    assert response.json["code"] == "invalid_credentials"


def test_lifecycle_problem_matches_closed_mobile_problem_contract(monkeypatch) -> None:
    secret = "s" * 64
    monkeypatch.setenv("OLDAP_MOBILE_MEDIA_SERVICE_JWT_SECRET", secret)
    app = Flask(__name__)
    app.register_blueprint(
        mobile_media_lifecycle_views.internal_mobile_media_lifecycle_bp
    )
    token = _token(
        secret,
        purpose=internal_auth.MOBILE_MEDIA_LIFECYCLE_TOKEN_PURPOSE,
        audience=internal_auth.MOBILE_MEDIA_LIFECYCLE_AUDIENCE,
    )

    response = app.test_client().post(
        "/internal/mobile-media/v1/lifecycle-events/claims",
        json={"unexpected": WORKER},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert set(response.json) == {
        "type",
        "title",
        "status",
        "code",
        "traceId",
        "retryable",
    }


def test_lifecycle_routes_return_and_complete_the_exact_claim(monkeypatch) -> None:
    secret = "s" * 64
    monkeypatch.setenv("OLDAP_MOBILE_MEDIA_SERVICE_JWT_SECRET", secret)
    claim = SimpleNamespace(
        event_id=EVENT,
        to_dict=lambda: {
            "eventId": EVENT,
            "claimId": CLAIM,
            "workerId": WORKER,
            "kind": "staging_deleted",
            "uploadId": UPLOAD,
            "clientAssetId": ASSET,
            "ownerUserIri": OWNER,
            "stagingAreaId": AREA,
            "resourceIri": RESOURCE,
            "checksum": CHECKSUM,
            "occurredAt": "2026-09-02T12:00:00Z",
            "leaseExpiresAt": "2026-09-02T12:05:00Z",
        },
    )

    class Outbox:
        def __init__(self) -> None:
            self.completed = []

        def claim_next(self, worker_id):
            assert worker_id == WORKER
            return claim

        def complete(self, event_id, claim_id, worker_id):
            self.completed.append((event_id, claim_id, worker_id))

    class ImmediateLock:
        def run(self, operation):
            return operation()

    outbox = Outbox()
    monkeypatch.setattr(mobile_media_lifecycle_views, "_outbox", lambda: outbox)
    monkeypatch.setattr(
        mobile_media_lifecycle_views, "RedisMobileMediaCommitLock", ImmediateLock
    )
    app = Flask(__name__)
    app.register_blueprint(
        mobile_media_lifecycle_views.internal_mobile_media_lifecycle_bp
    )
    client = app.test_client()
    token = _token(
        secret,
        purpose=internal_auth.MOBILE_MEDIA_LIFECYCLE_TOKEN_PURPOSE,
        audience=internal_auth.MOBILE_MEDIA_LIFECYCLE_AUDIENCE,
    )
    headers = {"Authorization": f"Bearer {token}"}

    claimed = client.post(
        "/internal/mobile-media/v1/lifecycle-events/claims",
        json={"workerId": WORKER},
        headers=headers,
    )
    completed = client.post(
        f"/internal/mobile-media/v1/lifecycle-events/{EVENT}/complete",
        json={"claimId": CLAIM, "workerId": WORKER},
        headers=headers,
    )

    assert claimed.status_code == 200
    assert claimed.json == claim.to_dict()
    assert completed.status_code == 200
    assert completed.json == {"eventId": EVENT, "state": "delivered"}
    assert outbox.completed == [(EVENT, CLAIM, WORKER)]
