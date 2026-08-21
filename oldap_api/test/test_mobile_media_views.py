"""Internal mobile-media HTTP authentication and error-contract tests."""

from datetime import UTC, datetime, timedelta

import jwt
from flask import Flask

from oldap_api.factory import factory
from oldap_api.mobile_media.domain import (
    MobileMediaCommitConflict,
    MobileMediaCommitResult,
)
from oldap_api.mobile_media.internal_auth import (
    MOBILE_MEDIA_AUDIENCE,
    MOBILE_MEDIA_SUBJECT,
    MOBILE_MEDIA_TOKEN_PURPOSE,
    MOBILE_MEDIA_TOKEN_TYPE,
)
from oldap_api.test.test_mobile_media_domain import (
    CHECKSUM,
    CLIENT_ASSET_ID,
    EVENT_ID,
    UPLOAD_ID,
    commit_request,
)
from oldap_api.views import mobile_media_views

SECRET = "mobile-media-service-secret-with-at-least-32-bytes"
ISSUER = "https://issuer.example"


def _token(
    *,
    secret: str = SECRET,
    token_type: str = MOBILE_MEDIA_TOKEN_TYPE,
    purpose: str = MOBILE_MEDIA_TOKEN_PURPOSE,
    subject: str = MOBILE_MEDIA_SUBJECT,
    audience: str = MOBILE_MEDIA_AUDIENCE,
    lifetime: timedelta = timedelta(minutes=1),
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "typ": token_type,
            "purpose": purpose,
            "sub": subject,
            "iat": now,
            "exp": now + lifetime,
            "iss": ISSUER,
            "aud": audience,
        },
        secret,
        algorithm="HS256",
    )


def _client(monkeypatch, service):
    monkeypatch.setenv("OLDAP_MOBILE_MEDIA_SERVICE_JWT_SECRET", SECRET)
    monkeypatch.setenv("OLDAP_JWT_ISSUER", ISSUER)
    monkeypatch.setattr(mobile_media_views, "_internal_service", lambda: service)
    app = Flask(__name__)
    app.register_blueprint(mobile_media_views.internal_mobile_media_bp)
    app.config.update(TESTING=True)
    return app.test_client()


class SuccessfulService:
    def commit(self, upload_id, data):
        assert upload_id == UPLOAD_ID
        assert data == commit_request()
        return MobileMediaCommitResult(
            event_id=EVENT_ID,
            upload_id=UPLOAD_ID,
            client_asset_id=CLIENT_ASSET_ID,
            staging_area_id=commit_request()["stagingAreaId"],
            asset_id=CLIENT_ASSET_ID,
            resource_iri="urn:uuid:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            checksum=CHECKSUM,
            committed_at=datetime(2026, 8, 20, 16, 0, tzinfo=UTC),
        )


def test_exact_service_token_and_closed_route_return_durable_result(
    monkeypatch,
) -> None:
    client = _client(monkeypatch, SuccessfulService())

    response = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token()}", "X-Request-ID": "request-1"},
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.get_json() == {
        "eventId": EVENT_ID,
        "uploadId": UPLOAD_ID,
        "clientAssetId": CLIENT_ASSET_ID,
        "stagingAreaId": commit_request()["stagingAreaId"],
        "assetId": CLIENT_ASSET_ID,
        "resourceIri": "urn:uuid:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "checksum": CHECKSUM,
        "committedAt": "2026-08-20T16:00:00Z",
    }


def test_missing_wrong_purpose_and_overlong_tokens_are_rejected(monkeypatch) -> None:
    client = _client(monkeypatch, SuccessfulService())
    missing = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
    )
    wrong_purpose = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token(purpose='zip-import')}"},
    )
    overlong = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token(lifetime=timedelta(minutes=6))}"},
    )
    wrong_secret = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={
            "Authorization": (
                "Bearer "
                f"{_token(secret='different-purpose-secret-with-at-least-32-bytes')}"
            )
        },
    )
    wrong_audience = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token(audience='oldap-api')}"},
    )
    wrong_type = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token(token_type='import-service')}"},
    )
    wrong_subject = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token(subject='other-service')}"},
    )
    expired = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token(lifetime=timedelta(seconds=-1))}"},
    )

    for response in (
        missing,
        wrong_purpose,
        overlong,
        wrong_secret,
        wrong_audience,
        wrong_type,
        wrong_subject,
        expired,
    ):
        assert response.status_code == 401
        assert response.content_type == "application/problem+json"
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.get_json()["code"] == "invalid_credentials"
        assert response.get_json()["retryable"] is False


def test_shared_or_missing_service_secret_fails_closed(monkeypatch) -> None:
    client = _client(monkeypatch, SuccessfulService())
    monkeypatch.setenv("OLDAP_ACCESS_JWT_SECRET", SECRET)

    shared = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token()}"},
    )
    monkeypatch.delenv("OLDAP_MOBILE_MEDIA_SERVICE_JWT_SECRET")
    missing = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token()}"},
    )

    for response in (shared, missing):
        assert response.status_code == 503
        assert response.get_json()["code"] == "authentication_unavailable"
        assert response.get_json()["retryable"] is True


def test_conflicts_do_not_expose_foreign_receipt_or_resource_details(
    monkeypatch,
) -> None:
    class ConflictingService:
        def commit(self, upload_id, data):
            raise MobileMediaCommitConflict("foreign resource urn:secret")

    client = _client(monkeypatch, ConflictingService())
    response = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 409
    assert response.content_type == "application/problem+json"
    assert response.get_json()["code"] == "client_asset_conflict"
    assert "foreign" not in response.get_data(as_text=True)
    assert "urn:secret" not in response.get_data(as_text=True)


def test_untrusted_trace_id_is_not_reflected(monkeypatch) -> None:
    client = _client(monkeypatch, SuccessfulService())
    response = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"X-Request-ID": "not safe whitespace"},
    )

    assert response.status_code == 401
    assert response.get_json()["traceId"] != "not safe whitespace"


def test_unexpected_backend_failures_keep_the_stable_private_error_contract(
    monkeypatch,
) -> None:
    class BrokenService:
        def commit(self, upload_id, data):
            raise ValueError("private implementation detail")

    client = _client(monkeypatch, BrokenService())
    response = client.post(
        f"/internal/mobile-media/v1/uploads/{UPLOAD_ID}/commit",
        json=commit_request(),
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 503
    assert response.content_type == "application/problem+json"
    assert response.get_json()["code"] == "upstream_unavailable"
    assert "private implementation detail" not in response.get_data(as_text=True)


def test_factory_keeps_existing_routes_and_registers_only_the_new_commit() -> None:
    app = factory()
    rules = {str(rule): set(rule.methods) for rule in app.url_map.iter_rules()}

    assert "/admin/auth/<userid>" in rules
    assert "/mobile/v1/auth/login" in rules
    assert "/imports" in rules
    assert rules["/internal/mobile-media/v1/uploads/<upload_id>/commit"] == {
        "POST",
        "OPTIONS",
    }
