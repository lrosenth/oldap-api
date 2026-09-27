"""Mail routing security and compatibility without live services."""

import json
from dataclasses import replace

import pytest
from flask import Flask

from oldap_api.frontend_links import (
    registry,
    frontend_for_origin,
    mail_link,
    FrontendRequestError,
)
from oldap_api.test.test_export_manifest import bound_job
from oldap_api.exports.domain import ExportJob
from oldap_api.imports.domain import ImportJob
from oldap_api.test.test_import_views import _client
from oldap_api.views import auth_views


def configure(monkeypatch, tmp_path):
    entry = {
        "origin": "https://salsah.org",
        "display_name": "SALSAH",
        "routes": {
            "password_reset": "/password-reset",
            "import_status": "/imports/{import_id}",
            "export_status": "/exports/{export_id}",
        },
    }
    path = tmp_path / "frontends.json"
    path.write_text(json.dumps({"salsah": entry}))
    monkeypatch.setenv("OLDAP_FRONTENDS_FILE", str(path))
    return path, entry


def test_selected_links_and_legacy(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    monkeypatch.setenv("OLDAP_PUBLIC_APP_URL", "https://fasnacht.digital")
    monkeypatch.setenv("OLDAP_PASSWORD_RESET_FRONTEND_URL", "https://fasnacht.digital")
    assert frontend_for_origin("https://salsah.org") == "salsah"
    assert frontend_for_origin(None) is None
    assert (
        mail_link(None, "import_status", import_id="123")
        == "https://fasnacht.digital/imports/123"
    )
    assert (
        mail_link("salsah", "export_status", export_id="a/b?x")
        == "https://salsah.org/exports/a%2Fb%3Fx"
    )
    assert (
        auth_views._password_reset_link("a.b.c", "salsah")
        == "https://salsah.org/password-reset?token=a%2Eb%2Ec"
    )
    with pytest.raises(FrontendRequestError):
        frontend_for_origin("https://salsah.org.evil.example")
    with pytest.raises(RuntimeError):
        mail_link("removed", "password_reset")


@pytest.mark.parametrize(
    "route",
    [
        "https://evil.org",
        "//evil.org",
        "/\\evil",
        "/%2f%2fevil",
        "/a/../b",
        "/reset?next=x",
        "/{token}",
        "/{import_id.__class__}",
    ],
)
def test_reject_unsafe_routes(monkeypatch, tmp_path, route):
    path, entry = configure(monkeypatch, tmp_path)
    entry["routes"]["password_reset"] = route
    path.write_text(json.dumps({"salsah": entry}))
    with pytest.raises(RuntimeError):
        registry()


def test_bad_registry_does_not_fall_back(monkeypatch, tmp_path):
    path, _ = configure(monkeypatch, tmp_path)
    path.write_text("{")
    with pytest.raises(RuntimeError):
        frontend_for_origin(None)


def test_export_roundtrip_preserves_destination():
    job, _ = bound_job()
    routed = replace(job, frontend_id="salsah")
    assert ExportJob.from_dict(routed.to_dict(internal=True)).frontend_id == "salsah"
    assert "frontendId" not in routed.to_dict()
    assert ExportJob.from_dict(job.to_dict(internal=True)).frontend_id is None


def test_reset_rejects_untrusted_origin_before_lookup(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    monkeypatch.setattr(
        auth_views,
        "_password_reset_connection",
        lambda: pytest.fail("No lookup permitted"),
    )
    app = Flask(__name__)
    app.register_blueprint(auth_views.auth_bp)
    response = app.test_client().post(
        "/admin/auth/password-reset/request",
        json={"userId": "alice"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 400


def test_import_creation_persists_routing_across_worker_roundtrip(
    monkeypatch, tmp_path
):
    from oldap_api.test.test_import_views import _body
    from oldap_api.views import import_views

    configure(monkeypatch, tmp_path)
    client = _client(monkeypatch)
    response = client.post(
        "/imports",
        json=_body(),
        headers={
            "Authorization": "Bearer valid-test-token",
            "Origin": "https://salsah.org",
        },
    )
    assert response.status_code == 201
    service = import_views._service(None)
    job = service._repository.get(response.json["job"]["importId"])
    assert job.frontend_id == "salsah"
    assert ImportJob.from_dict(job.to_dict(internal=True)).frontend_id == "salsah"
    assert "frontendId" not in job.to_dict()
    legacy = replace(job, frontend_id=None).to_dict(internal=True)
    assert ImportJob.from_dict(legacy).frontend_id is None
    invalid = client.post(
        "/imports",
        json=_body(),
        headers={
            "Authorization": "Bearer valid-test-token",
            "Origin": "https://evil.example",
        },
    )
    assert invalid.status_code == 400


def test_export_creation_persists_routing(monkeypatch, tmp_path):
    from oldap_api.test.test_export_views import _client as export_client, _body
    from oldap_api.views import export_views

    configure(monkeypatch, tmp_path)
    client = export_client(monkeypatch)
    response = client.post(
        "/exports",
        json=_body(),
        headers={
            "Authorization": "Bearer valid-test-token",
            "Origin": "https://salsah.org",
        },
    )
    assert response.status_code == 202
    job = export_views._service(None)._repository.get(response.json["exportId"])
    assert ExportJob.from_dict(job.to_dict(internal=True)).frontend_id == "salsah"


def test_reset_request_routes_before_sending_and_rejects_url_injection(
    monkeypatch, tmp_path
):
    from types import SimpleNamespace

    configure(monkeypatch, tmp_path)
    user = SimpleNamespace(update=lambda: None)
    monkeypatch.setattr(auth_views, "_password_reset_connection", lambda: object())
    monkeypatch.setattr(
        auth_views,
        "_resolve_password_reset_user",
        lambda connection, data: (user, None),
    )
    monkeypatch.setattr(
        auth_views, "_build_password_reset_token", lambda *args: "a.b.c"
    )
    sent = []
    monkeypatch.setattr(
        auth_views,
        "_send_password_reset_email",
        lambda user, link, **kwargs: sent.append((link, kwargs)),
    )
    app = Flask(__name__)
    app.register_blueprint(auth_views.auth_bp)
    client = app.test_client()
    response = client.post(
        "/admin/auth/password-reset/request",
        json={"userId": "alice"},
        headers={"Origin": "https://salsah.org"},
    )
    assert response.status_code == 200
    assert sent == [
        (
            "https://salsah.org/password-reset?token=a%2Eb%2Ec",
            {"identified_by_email": False, "frontend_id": "salsah"},
        )
    ]
    response = client.post(
        "/admin/auth/password-reset/request",
        json={"userId": "alice", "url": "https://evil.example"},
        headers={"Origin": "https://salsah.org"},
    )
    assert response.status_code == 400
    assert len(sent) == 1


def test_origin_aliases_and_display_name_escaping(monkeypatch, tmp_path):
    from types import SimpleNamespace

    path, entry = configure(monkeypatch, tmp_path)
    entry["origins"] = ["https://legacy.example", "https://salsah.org"]
    path.write_text(json.dumps({"salsah": entry}))
    assert frontend_for_origin("https://legacy.example") == "salsah"
    user = SimpleNamespace(userId="alice", givenName="Alice", familyName="Example")
    _, html = auth_views._password_reset_email_content(
        user, "https://salsah.org/password-reset", False, "<Application>"
    )
    assert "&lt;Application&gt;" in html
    assert "<Application>" not in html
