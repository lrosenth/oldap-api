"""Unit tests for the centralized bearer-authentication boundary."""

import requests
from flask import Flask, jsonify

from oldap_api.authentication import authenticated_connection, require_auth
from oldap_api.factory import factory
from oldap_api.views import auth_views
from oldaplib.src.authentication import AuthorizationContext, TokenCodec, TokenSettings
from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.in_project import InProjectClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName

ACCESS_SECRET = "boundary-access-secret-with-at-least-32-bytes"
REFRESH_SECRET = "boundary-refresh-secret-with-at-least-32-bytes"


def _codec() -> TokenCodec:
    return TokenCodec(
        TokenSettings(
            access_secret=ACCESS_SECRET,
            refresh_secret=REFRESH_SECRET,
        )
    )


def _access_token() -> str:
    context = AuthorizationContext(
        userIri=Iri("https://example.org/users/tester"),
        userId=Xsd_NCName("tester"),
        inProject=InProjectClass(),
        hasRole=ObservableDict(),
    )
    return _codec().issue_access_token(context)


def _app() -> Flask:
    app = Flask(__name__)

    @app.get("/protected")
    @require_auth
    def protected():
        return jsonify({"userId": str(authenticated_connection().userid)})

    return app


def test_valid_access_token_reaches_view(monkeypatch):
    monkeypatch.setenv("OLDAP_ACCESS_JWT_SECRET", ACCESS_SECRET)
    response = (
        _app()
        .test_client()
        .get("/protected", headers={"Authorization": f"Bearer {_access_token()}"})
    )
    assert response.status_code == 200
    assert response.json == {"userId": "tester"}


def test_missing_malformed_and_invalid_credentials_are_uniform(monkeypatch):
    monkeypatch.setenv("OLDAP_ACCESS_JWT_SECRET", ACCESS_SECRET)
    client = _app().test_client()
    headers = (
        None,
        {"Authorization": "Basic credentials"},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer invalid-token"},
    )
    for header in headers:
        response = client.get("/protected", headers=header)
        assert response.status_code == 401
        assert response.json == {"message": "Authentication required."}
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.headers["Cache-Control"] == "no-store"


def test_refresh_token_is_not_accepted_as_bearer(monkeypatch):
    monkeypatch.setenv("OLDAP_ACCESS_JWT_SECRET", ACCESS_SECRET)
    refresh = _codec().issue_refresh_token("tester", 0)
    response = (
        _app()
        .test_client()
        .get("/protected", headers={"Authorization": f"Bearer {refresh}"})
    )
    assert response.status_code == 401
    assert response.json == {"message": "Authentication required."}


def test_missing_access_secret_is_operational_error(monkeypatch):
    monkeypatch.delenv("OLDAP_ACCESS_JWT_SECRET", raising=False)
    response = (
        _app()
        .test_client()
        .get("/protected", headers={"Authorization": f"Bearer {_access_token()}"})
    )
    assert response.status_code == 503
    assert response.json == {"message": "Authentication required."}


def test_every_protected_route_uses_shared_authentication_boundary():
    """Keep protected blueprints from reintroducing local token parsing."""
    app = factory()
    protected_blueprints = {
        "user",
        "project",
        "role",
        "resource",
        "hlist",
        "datamodel",
        "instance",
        "imports",
    }
    unprotected_endpoints = sorted(
        rule.endpoint
        for rule in app.url_map.iter_rules()
        if rule.endpoint.partition(".")[0] in protected_blueprints
        and not getattr(
            app.view_functions[rule.endpoint], "_oldap_requires_auth", False
        )
    )

    assert unprotected_endpoints == []


def test_browser_login_maps_backend_transport_failure_to_cache_safe_503(monkeypatch):
    """Browser login must not turn a GraphDB outage into a cacheable 500."""

    def unavailable_connection(*args, **kwargs):
        raise requests.ConnectionError("GraphDB unavailable")

    monkeypatch.setattr(auth_views, "Connection", unavailable_connection)
    response = (
        factory().test_client().post("/admin/auth/rosenth", json={"password": "secret"})
    )

    assert response.status_code == 503
    assert response.json == {"message": "Authentication is unavailable."}
    assert response.headers["Cache-Control"] == "no-store"


def test_browser_refresh_maps_backend_transport_failure_to_cache_safe_503(monkeypatch):
    """Refresh must report a backend outage while clearing no valid token state."""

    def unavailable_authentication_connection(*args, **kwargs):
        raise requests.ConnectionError("GraphDB unavailable")

    monkeypatch.setenv("OLDAP_REFRESH_JWT_SECRET", REFRESH_SECRET)
    monkeypatch.setattr(
        auth_views,
        "_authentication_connection",
        unavailable_authentication_connection,
    )
    refresh = _codec().issue_refresh_token("tester", 0)
    client = factory().test_client()
    client.set_cookie("oldap_refresh", refresh, path="/admin/auth")

    response = client.post("/admin/auth/refresh")

    assert response.status_code == 503
    assert response.json == {"message": "Authentication is unavailable."}
    assert response.headers["Cache-Control"] == "no-store"


def test_browser_logout_maps_backend_transport_failure_to_cache_safe_503(monkeypatch):
    """Logout must clear the cookie even when revocation cannot reach GraphDB."""

    def unavailable_authentication_connection(*args, **kwargs):
        raise requests.ConnectionError("GraphDB unavailable")

    monkeypatch.setenv("OLDAP_REFRESH_JWT_SECRET", REFRESH_SECRET)
    monkeypatch.setattr(
        auth_views, "_authentication_connection", unavailable_authentication_connection
    )
    refresh = _codec().issue_refresh_token("tester", 0)
    client = factory().test_client()
    client.set_cookie("oldap_refresh", refresh, path="/admin/auth")

    response = client.post("/admin/auth/logout")

    assert response.status_code == 503
    assert response.json == {"message": "Authentication is unavailable."}
    assert response.headers["Cache-Control"] == "no-store"
    assert "Max-Age=0" in response.headers["Set-Cookie"]
