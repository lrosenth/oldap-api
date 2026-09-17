"""Read-only, generic and bounded placement-status contract tests."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.xsd.iri import Iri
from oldap_api import archive_placement as service


def policy():
    context = Context(name="PLACEMENT_STATUS_TEST")
    context["museum"] = "https://museum.example/"
    return SimpleNamespace(enabled=True, context=context,
        connection=SimpleNamespace(userIri=Iri("urn:test:actor")),
        project=SimpleNamespace(projectShortName="museum"),
        media_classes=("https://museum.example/Media",),
        publication={"rootClassIris": ["https://museum.example/Object"],
                     "mediaToRootPropertyIri": "https://museum.example/represents"})


@pytest.mark.parametrize("body", [None, {}, {"targets": []}, {"targets": [{}]},
    {"targets": [{"iri": "urn:test:a", "kind": "wrong"}]},
    {"targets": [{"iri": "urn:test:a", "kind": "entry", "extra": True}]},
    {"targets": [{"iri": "urn:test:a", "kind": "entry"}]*501}])
def test_reject_invalid_batches_before_policy_or_query(monkeypatch, body):
    load = Mock(side_effect=AssertionError("must validate before database access"))
    monkeypatch.setattr(service.ArchivePolicy, "load", load)
    with pytest.raises(OldapErrorValue):
        service.placement_status(object(), "museum", body)
    load.assert_not_called()


def test_one_aggregate_for_whole_batch_and_generic_policy(monkeypatch):
    monkeypatch.setattr(service.ArchivePolicy, "load", lambda *args: policy())
    query = Mock(return_value={"results": {"bindings": [
        {"key": {"value": "urn:test:a"}, "total": {"value": "3"}, "unassigned": {"value": "1"}}]}})
    monkeypatch.setattr(service, "resource_query", query)
    result = service.placement_status(object(), "museum", {"targets": [
        {"iri": "urn:test:a", "kind": "entry"}, {"iri": "urn:test:b", "kind": "media"}]})
    assert result == {"items": [{"iri": "urn:test:a", "mediaCount": 3, "unassignedCount": 1}]}
    query.assert_called_once()
    sparql = query.call_args.args[1]
    assert "fasnacht" not in sparql
    assert 'VALUES (?key ?target ?kind)' in sparql
    assert "COUNT(DISTINCT ?media)" in sparql
    assert "COUNT(DISTINCT ?free)" in sparql
    assert "targetAccess_role" in sparql and "mediaAccess_role" in sparql
    assert "createdBy" not in sparql
    assert "?unit a shared:ArchiveUnit ; shared:hasMediaObject ?media" in sparql
    assert "SELECT ?key" in sparql  # no destination identity in response


def test_endpoint_is_authenticated_and_uncacheable(monkeypatch):
    from flask import Flask
    from oldap_api.views import archive_structure_views as views
    app = Flask(__name__)
    app.register_blueprint(views.archive_structure_bp)
    endpoint, args = app.url_map.bind("localhost").match("/archive/museum/placement-status", method="POST")
    assert endpoint.endswith("content_placement_status") and args == {"project": "museum"}
    monkeypatch.setattr(views, "authenticated_connection", lambda: object())
    monkeypatch.setattr(service, "placement_status", lambda *args: {"items": []})
    with app.test_request_context(json={"targets": [{"iri": "urn:test:a", "kind": "entry"}]}):
        response, status = views.content_placement_status.__wrapped__("museum")
        assert status == 200 and response.get_json() == {"items": []}
        assert views.private_response(response).headers["Cache-Control"] == "no-store"
