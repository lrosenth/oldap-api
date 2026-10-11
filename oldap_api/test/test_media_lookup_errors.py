"""Media lookup HTTP contracts without GraphDB or authentication side effects."""

from unittest.mock import Mock

import pytest
from flask import Flask

from oldap_api.views import instance_views as views
from oldaplib.src.helpers.oldaperror import (
    OldapErrorConfiguration,
    OldapErrorNotFound,
    OldapErrorValue,
)


@pytest.mark.parametrize(
    "endpoint,lookup",
    [
        ("/mediaobject/id/missing", "get_media_object_by_id"),
        ("/mediaobject/iri/urn:uuid:missing", "get_media_object_by_iri"),
    ],
)
@pytest.mark.parametrize(
    "error,result,expected",
    [
        (OldapErrorNotFound("internal lookup details"), None, 404),
        (None, None, 404),
        (OldapErrorValue("invalid request"), None, 400),
        (OldapErrorConfiguration("service unavailable"), None, 503),
        (None, {"iri": "urn:uuid:present"}, 200),
    ],
)
def test_media_lookup_status(monkeypatch, endpoint, lookup, error, result, expected):
    """Only missing results map to 404; successful metadata still uses its serializer."""
    app = Flask(__name__)
    app.register_blueprint(views.instance_bp)
    # Exercise Flask routing/response conversion independently of JWT verification.
    for name in ("media_object_by_id", "media_object_by_iri"):
        app.view_functions["instance." + name] = getattr(views, name).__wrapped__
    monkeypatch.setattr(views, "authenticated_connection", lambda: object())
    resolver = Mock(side_effect=error, return_value=result)
    monkeypatch.setattr(views.ResourceInstance, lookup, resolver)
    serializer = Mock(return_value={"serialized": True})
    monkeypatch.setattr(views, "media_object_json_response", serializer)
    response = app.test_client().get("/data" + endpoint)
    assert response.status_code == expected
    resolver.assert_called_once()
    if expected == 404:
        assert response.json == {"message": "MediaObject not found"}
    if expected == 200:
        serializer.assert_called_once_with(result)
        assert response.json == {"serialized": True}
    else:
        serializer.assert_not_called()
