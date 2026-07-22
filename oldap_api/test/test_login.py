"""Integration tests for login, refresh, and global logout."""

from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

import jwt
import requests
from oldaplib.src.authentication import TokenCodec
from oldaplib.src.helpers.oldaperror import OldapError

from oldap_api.views import auth_views


def _refresh_token(response) -> str:
    cookies = SimpleCookie()
    cookies.load(response.headers["Set-Cookie"])
    return cookies["oldap_refresh"].value


def _decode_access(token: str, secret: str) -> dict:
    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        issuer="https://oldap.org",
        audience="oldap-api",
    )


def test_login_succeed(client, connection_manager):
    response = client.post("/admin/auth/rosenth", json={"password": "RioGrande"})
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    result = response.json
    assert result["message"] == "Login succeeded"
    assert result["tokenType"] == "Bearer"
    assert result["expiresIn"] == 900
    assert result["accessToken"] == result["token"]

    payload = _decode_access(result["accessToken"], connection_manager.access_secret)
    assert payload["typ"] == "access"
    assert payload["sub"] == "rosenth"
    assert payload["userIri"] == "https://orcid.org/0000-0003-1681-4036"
    assert "userdata" not in payload

    refresh = _refresh_token(response)
    refresh_payload = jwt.decode(
        refresh,
        connection_manager.refresh_secret,
        algorithms=["HS256"],
        issuer="https://oldap.org",
        audience="oldap-api-refresh",
    )
    assert refresh_payload["typ"] == "refresh"
    set_cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=Lax" in set_cookie
    assert "Path=/admin/auth" in set_cookie


def test_refresh_and_global_logout(client, connection_manager):
    login = client.post("/admin/auth/rosenth", json={"password": "RioGrande"})
    old_refresh = _refresh_token(login)

    refreshed = client.post("/admin/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.headers["Cache-Control"] == "no-store"
    assert (
        _decode_access(refreshed.json["accessToken"], connection_manager.access_secret)[
            "sub"
        ]
        == "rosenth"
    )
    assert "Set-Cookie" not in refreshed.headers

    logout = client.post("/admin/auth/logout")
    assert logout.status_code == 204
    assert logout.headers["Cache-Control"] == "no-store"
    assert "Max-Age=0" in logout.headers["Set-Cookie"]

    client.set_cookie("oldap_refresh", old_refresh, path="/admin/auth")
    rejected = client.post("/admin/auth/refresh")
    assert rejected.status_code == 401
    assert rejected.json == {"message": "Authentication failed."}


def test_refresh_rejects_invalid_cookie_and_origin(client):
    client.set_cookie("oldap_refresh", "not-a-jwt", path="/admin/auth")
    invalid = client.post("/admin/auth/refresh")
    assert invalid.status_code == 401

    login = client.post("/admin/auth/rosenth", json={"password": "RioGrande"})
    assert login.status_code == 200
    forbidden = client.post(
        "/admin/auth/refresh", headers={"Origin": "https://evil.example"}
    )
    assert forbidden.status_code == 403


def test_mobile_login_returns_tokens_without_cookie(client, connection_manager):
    response = client.post(
        "/mobile/v1/auth/login",
        json={"userId": "rosenth", "password": "RioGrande"},
    )
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert "Set-Cookie" not in response.headers
    assert response.json["tokenType"] == "Bearer"
    assert response.json["expiresIn"] == 900
    assert response.json["refreshTokenExpiresIn"] == 1_209_600
    assert "token" not in response.json

    access_payload = _decode_access(
        response.json["accessToken"], connection_manager.access_secret
    )
    assert access_payload["typ"] == "access"
    assert access_payload["sub"] == "rosenth"

    refresh_payload = jwt.decode(
        response.json["refreshToken"],
        connection_manager.refresh_secret,
        algorithms=["HS256"],
        issuer="https://oldap.org",
        audience="oldap-api-refresh",
    )
    assert refresh_payload["typ"] == "refresh"
    assert refresh_payload["sub"] == "rosenth"


def test_mobile_refresh_is_stateless_and_cookie_free(client, connection_manager):
    login = client.post(
        "/mobile/v1/auth/login",
        json={"userId": "rosenth", "password": "RioGrande"},
    )
    refresh_token = login.json["refreshToken"]

    first = client.post(
        "/mobile/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    second = client.post(
        "/mobile/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )

    for response in (first, second):
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert "Set-Cookie" not in response.headers
        assert "refreshToken" not in response.json
        payload = _decode_access(
            response.json["accessToken"], connection_manager.access_secret
        )
        assert payload["sub"] == "rosenth"

    assert first.json["accessToken"] != second.json["accessToken"]


def test_mobile_refresh_rejects_wrong_token_purpose(client):
    login = client.post(
        "/mobile/v1/auth/login",
        json={"userId": "rosenth", "password": "RioGrande"},
    )
    media_token = TokenCodec.from_environment().issue_media_token(
        "rosenth", {"assetId": "review-asset"}
    )

    for token in (login.json["accessToken"], media_token):
        response = client.post(
            "/mobile/v1/auth/refresh",
            json={"refreshToken": token},
        )
        assert response.status_code == 401
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json == {
            "code": "refresh_token_invalid",
            "message": "Authentication failed.",
        }


def test_mobile_login_rejects_invalid_credentials_and_oversized_password(client):
    invalid = client.post(
        "/mobile/v1/auth/login",
        json={"userId": "rosenth", "password": "wrong-password"},
    )
    oversized = client.post(
        "/mobile/v1/auth/login",
        json={"userId": "rosenth", "password": "x" * 73},
    )
    invalid_unicode = client.post(
        "/mobile/v1/auth/login",
        json={"userId": "rosenth", "password": "\ud800"},
    )

    assert invalid.status_code == 401
    assert invalid.headers["WWW-Authenticate"] == "Bearer"
    assert invalid.headers["Cache-Control"] == "no-store"
    assert invalid.json["code"] == "invalid_credentials"
    assert oversized.status_code == 400
    assert oversized.headers["Cache-Control"] == "no-store"
    assert oversized.json["code"] == "validation_failed"
    assert invalid_unicode.status_code == 400
    assert invalid_unicode.headers["Cache-Control"] == "no-store"
    assert invalid_unicode.json["code"] == "validation_failed"


def test_mobile_refresh_rejects_expired_and_inactive_credentials(client):
    codec = TokenCodec.from_environment()
    expired = codec.issue_refresh_token(
        "rosenth",
        0,
        now=datetime.now(UTC)
        - timedelta(seconds=codec.settings.refresh_ttl_seconds + 1),
    )
    inactive = codec.issue_refresh_token("bugsbunny", 0)

    for token in (expired, inactive):
        response = client.post(
            "/mobile/v1/auth/refresh",
            json={"refreshToken": token},
        )
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json["code"] == "refresh_token_invalid"


def test_mobile_auth_maps_backend_outage_to_service_unavailable(client, monkeypatch):
    login = client.post(
        "/mobile/v1/auth/login",
        json={"userId": "rosenth", "password": "RioGrande"},
    )
    refresh_token = login.json["refreshToken"]

    def unavailable_connection(*args, **kwargs):
        raise requests.ConnectionError("GraphDB unavailable")

    monkeypatch.setattr(auth_views, "Connection", unavailable_connection)
    responses = (
        client.post(
            "/mobile/v1/auth/login",
            json={"userId": "rosenth", "password": "RioGrande"},
        ),
        client.post(
            "/mobile/v1/auth/refresh",
            json={"refreshToken": refresh_token},
        ),
    )

    for response in responses:
        assert response.status_code == 503
        assert response.content_type == "application/json"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json == {
            "code": "authentication_unavailable",
            "message": "Authentication is unavailable.",
        }

    def graphdb_http_error(*args, **kwargs):
        raise OldapError(503, "GraphDB unavailable")

    monkeypatch.setattr(auth_views, "Connection", graphdb_http_error)
    http_error = client.post(
        "/mobile/v1/auth/login",
        json={"userId": "rosenth", "password": "RioGrande"},
    )
    assert http_error.status_code == 503
    assert http_error.headers["Cache-Control"] == "no-store"
    assert http_error.json["code"] == "authentication_unavailable"

    def graphdb_query_error(*args, **kwargs):
        raise OldapError("GraphDB query failed")

    monkeypatch.setattr(auth_views, "_authentication_connection", lambda: object())
    monkeypatch.setattr(auth_views.User, "read", staticmethod(graphdb_query_error))
    query_error = client.post(
        "/mobile/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert query_error.status_code == 503
    assert query_error.headers["Cache-Control"] == "no-store"
    assert query_error.json["code"] == "authentication_unavailable"


def test_mobile_refresh_rejects_token_after_permission_change(client):
    root_login = client.post("/admin/auth/rosenth", json={"password": "RioGrande"})
    root_header = {"Authorization": f"Bearer {root_login.json['accessToken']}"}
    user_id = "mobilepermissions"
    created = client.put(
        f"/admin/user/{user_id}",
        json={
            "givenName": "Mobile",
            "familyName": "Permissions",
            "email": "mobile.permissions@example.org",
            "password": "mobilePassword",
            "hasRole": {"oldap:Unknown": "DATA_VIEW"},
        },
        headers=root_header,
    )
    assert created.status_code == 200

    try:
        login = client.post(
            "/mobile/v1/auth/login",
            json={"userId": user_id, "password": "mobilePassword"},
        )
        assert login.status_code == 200

        changed = client.post(
            f"/admin/user/{user_id}",
            json={"hasRole": {"del": ["oldap:Unknown"]}},
            headers=root_header,
        )
        assert changed.status_code == 200

        rejected = client.post(
            "/mobile/v1/auth/refresh",
            json={"refreshToken": login.json["refreshToken"]},
        )
        assert rejected.status_code == 401
        assert rejected.json["code"] == "refresh_token_invalid"
    finally:
        client.delete(f"/admin/user/{user_id}", headers=root_header)


def test_mobile_refresh_honors_global_auth_version_revocation(client):
    login = client.post(
        "/mobile/v1/auth/login",
        json={"userId": "rosenth", "password": "RioGrande"},
    )
    refresh_token = login.json["refreshToken"]
    client.set_cookie("oldap_refresh", refresh_token, path="/admin/auth")

    logout = client.post("/admin/auth/logout")
    assert logout.status_code == 204

    rejected = client.post(
        "/mobile/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert rejected.status_code == 401
    assert rejected.json["code"] == "refresh_token_invalid"


def test_mobile_auth_validates_json_without_setting_cookie(client):
    login = client.post("/mobile/v1/auth/login", json={"userId": "rosenth"})
    refresh = client.post("/mobile/v1/auth/refresh", json={})
    extra = client.post(
        "/mobile/v1/auth/refresh",
        json={"refreshToken": "token", "unexpected": True},
    )

    assert login.status_code == 400
    assert login.json["code"] == "validation_failed"
    assert "Set-Cookie" not in login.headers
    assert refresh.status_code == 400
    assert refresh.json["code"] == "validation_failed"
    assert "Set-Cookie" not in refresh.headers
    assert extra.status_code == 400
    assert extra.json["code"] == "validation_failed"


def test_unknown_login_has_no_refresh_session(client):
    response = client.post("/admin/auth/unknown", json={})
    assert response.status_code == 200
    cookie = response.headers["Set-Cookie"]
    assert "oldap_refresh=" in cookie
    assert "Max-Age=0" in cookie


def test_login_wrong_userid(client):
    response = client.post("/admin/auth/XZY", json={"password": "Rio Grande"})
    assert response.status_code == 404
    assert response.json["message"] == "Given user not found!"


def test_inactive_user_is_rejected(client):
    response = client.post("/admin/auth/bugsbunny", json={"password": "DuffyDuck"})
    assert response.status_code == 403


def test_password_change_revokes_existing_refresh(client):
    root_login = client.post("/admin/auth/rosenth", json={"password": "RioGrande"})
    root_header = {"Authorization": f"Bearer {root_login.json['accessToken']}"}
    user_id = "refreshpassword"
    created = client.put(
        f"/admin/user/{user_id}",
        json={
            "givenName": "Refresh",
            "familyName": "Password",
            "email": "refresh.password@example.org",
            "password": "oldPassword",
            "hasRole": {"oldap:Unknown": "DATA_VIEW"},
        },
        headers=root_header,
    )
    assert created.status_code == 200

    try:
        user_login = client.post(
            f"/admin/auth/{user_id}", json={"password": "oldPassword"}
        )
        assert user_login.status_code == 200
        old_refresh = _refresh_token(user_login)
        user_header = {"Authorization": f"Bearer {user_login.json['accessToken']}"}

        changed = client.post(
            f"/admin/user/{user_id}",
            json={
                "password": "newPassword",
            },
            headers=user_header,
        )
        assert changed.status_code == 200

        client.set_cookie("oldap_refresh", old_refresh, path="/admin/auth")
        rejected = client.post("/admin/auth/refresh")
        assert rejected.status_code == 401
    finally:
        client.delete(f"/admin/user/{user_id}", headers=root_header)


def test_login_no_password(client):
    response = client.post("/admin/auth/rosenth", json={"gaga": "RioGrande"})
    assert response.status_code == 400
    assert response.json["message"] == "Invalid content type, JSON required"


def test_legacy_logout_delegates_without_trusting_path_user(client):
    login = client.post("/admin/auth/rosenth", json={"password": "RioGrande"})
    assert login.status_code == 200
    response = client.delete("/admin/auth/not-rosenth")
    assert response.status_code == 200
    assert "Max-Age=0" in response.headers["Set-Cookie"]


def test_no_json(client, token_headers, testuser):
    response = client.post("/admin/auth/rosenth", data="Kein JSON!!")
    assert response.status_code == 400
    assert response.json["message"] == "JSON expected. Instead received None"
