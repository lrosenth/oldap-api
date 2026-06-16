from urllib.parse import parse_qs, urlparse

import jwt

from oldap_api.views import auth_views


def _configure_password_reset(monkeypatch, connection_manager):
    captured = {}

    monkeypatch.setenv("OLDAP_PASSWORD_RESET_ADMIN_USER", "rosenth")
    monkeypatch.setenv("OLDAP_PASSWORD_RESET_ADMIN_PASSWORD", "RioGrande")
    monkeypatch.setenv("OLDAP_PASSWORD_RESET_FRONTEND_URL", "https://app.example.org")
    monkeypatch.setenv("OLDAP_PASSWORD_RESET_JWT_SECRET", connection_manager.jwt_secret)

    def capture_email(user, link, identified_by_email):
        captured["user"] = user
        captured["link"] = link
        captured["identified_by_email"] = identified_by_email

    monkeypatch.setattr(auth_views, "_send_password_reset_email", capture_email)
    return captured


def _token_from_link(link):
    return parse_qs(urlparse(link).query)["token"][0]


def _create_user(client, header, user_id, email, password="oldPassword"):
    response = client.put(f"/admin/user/{user_id}", json={
        "givenName": "Reset",
        "familyName": "Candidate",
        "email": email,
        "password": password,
        "hasRole": {"oldap:Unknown": "DATA_VIEW"},
    }, headers=header)
    assert response.status_code == 200


def test_password_reset_request_and_confirm(client, connection_manager, token_headers, monkeypatch):
    header = token_headers[1]
    captured = _configure_password_reset(monkeypatch, connection_manager)
    user_id = "resetcandidate"
    email = "reset.candidate@example.org"

    _create_user(client, header, user_id, email)
    try:
        response = client.post("/admin/auth/password-reset/request", json={
            "userId": user_id,
        })
        assert response.status_code == 200
        assert "Email" in response.json["message"]
        first_token = _token_from_link(captured["link"])
        first_payload = jwt.decode(first_token, connection_manager.jwt_secret, algorithms=["HS256"])
        assert first_payload["purpose"] == "password-reset"
        assert first_payload["sub"] == user_id
        assert not captured["identified_by_email"]

        read_response = client.get(f"/admin/user/{user_id}", headers=header)
        assert read_response.status_code == 200
        assert read_response.json["passwordResetRequestAt"] == first_payload["resetRequestedAt"]

        response = client.post("/admin/auth/password-reset/request", json={
            "email": email,
        })
        assert response.status_code == 200
        assert captured["identified_by_email"]
        second_token = _token_from_link(captured["link"])
        second_payload = jwt.decode(second_token, connection_manager.jwt_secret, algorithms=["HS256"])
        assert second_payload["sub"] == user_id
        assert second_payload["resetRequestedAt"] != first_payload["resetRequestedAt"]

        response = client.post("/admin/auth/password-reset/confirm", json={
            "token": first_token,
            "password": "newPassword",
        })
        assert response.status_code == 400
        assert "invalid" in response.json["message"].lower()

        response = client.post("/admin/auth/password-reset/confirm", json={
            "token": second_token,
            "password": "newPassword",
        })
        assert response.status_code == 200

        read_response = client.get(f"/admin/user/{user_id}", headers=header)
        assert read_response.status_code == 200
        assert read_response.json["passwordResetRequestAt"] is None

        login = client.post(f"/admin/auth/{user_id}", json={"password": "newPassword"})
        assert login.status_code == 200
        assert login.json["message"] == "Login succeeded"
    finally:
        client.delete(f"/admin/user/{user_id}", headers=header)


def test_password_reset_request_needs_unique_user(client, connection_manager, token_headers, monkeypatch):
    header = token_headers[1]
    _configure_password_reset(monkeypatch, connection_manager)

    response = client.post("/admin/auth/password-reset/request", json={
        "email": "does.not.exist@example.org",
    })
    assert response.status_code == 409
    assert response.json["message"] == "Passwort reset unmöglich, kontaktieren sie info@fasnacht.digital"

    _create_user(client, header, "resetdup1", "shared.reset@example.org")
    _create_user(client, header, "resetdup2", "shared.reset@example.org")
    try:
        response = client.post("/admin/auth/password-reset/request", json={
            "email": "shared.reset@example.org",
        })
        assert response.status_code == 409
        assert response.json["message"] == "Passwort reset unmöglich, kontaktieren sie info@fasnacht.digital"
    finally:
        client.delete("/admin/user/resetdup1", headers=header)
        client.delete("/admin/user/resetdup2", headers=header)


def test_password_reset_confirm_rejects_expired_token(client, connection_manager, token_headers, monkeypatch):
    header = token_headers[1]
    captured = _configure_password_reset(monkeypatch, connection_manager)
    user_id = "resetexpired"

    _create_user(client, header, user_id, "reset.expired@example.org")
    try:
        response = client.post("/admin/auth/password-reset/request", json={
            "userId": user_id,
        })
        assert response.status_code == 200
        payload = jwt.decode(_token_from_link(captured["link"]), connection_manager.jwt_secret, algorithms=["HS256"])
        payload["exp"] = 1
        expired_token = jwt.encode(payload, connection_manager.jwt_secret, algorithm="HS256")

        response = client.post("/admin/auth/password-reset/confirm", json={
            "token": expired_token,
            "password": "newPassword",
        })
        assert response.status_code == 400
        assert "expired" in response.json["message"]
    finally:
        client.delete(f"/admin/user/{user_id}", headers=header)
