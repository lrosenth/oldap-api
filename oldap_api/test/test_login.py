"""Integration tests for login, refresh, and global logout."""

from http.cookies import SimpleCookie

import jwt


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
