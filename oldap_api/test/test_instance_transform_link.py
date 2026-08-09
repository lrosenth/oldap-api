"""HTTP contract tests for atomic links created during class transformation."""

from types import SimpleNamespace

from oldap_api.views import instance_views
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def test_transform_forwards_atomic_link_contract(client, token_headers, monkeypatch):
    """The endpoint passes the selected archive unit into oldaplib's transaction."""
    calls = {}
    media_iri = "urn:uuid:00000000-0000-0000-0000-000000000101"
    archive_unit_iri = "urn:uuid:00000000-0000-0000-0000-000000000102"

    class FakeInstance:
        def transform_class(self, target_class, **kwargs):
            calls["target_class"] = target_class
            calls["kwargs"] = kwargs
            return SimpleNamespace(iri=Iri(media_iri), name=Xsd_QName(target_class))

    class FakeFactory:
        def __init__(self, con, project):
            calls["project"] = project

        def read(self, iri):
            calls["read"] = iri
            return FakeInstance()

    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", FakeFactory)
    response = client.post(
        f"/data/test/{media_iri}/transform",
        json={
            "expectedSourceClass": "shared:StagingMediaObject",
            "preserveClass": "shared:MediaObject",
            "targetClass": "test:MediaLibraryEntry",
            "properties": {"test:caption": ["Archive draft"]},
            "linkFrom": {
                "resourceIri": archive_unit_iri,
                "property": "shared:hasMediaObject",
            },
        },
        headers=token_headers[1],
    )

    assert response.status_code == 200
    assert calls["project"] == "test"
    assert calls["read"] == Iri(media_iri)
    assert calls["kwargs"]["link_from_iri"] == archive_unit_iri
    assert calls["kwargs"]["link_from_property"] == "shared:hasMediaObject"


def test_transform_rejects_incomplete_or_unknown_link_contract(client, token_headers):
    """Malformed relation requests fail before any resource mutation."""
    media_iri = "urn:uuid:00000000-0000-0000-0000-000000000103"
    base = {
        "preserveClass": "shared:MediaObject",
        "targetClass": "test:MediaLibraryEntry",
    }

    missing_property = client.post(
        f"/data/test/{media_iri}/transform",
        json={**base, "linkFrom": {"resourceIri": "urn:archive:unit"}},
        headers=token_headers[1],
    )
    unknown_field = client.post(
        f"/data/test/{media_iri}/transform",
        json={
            **base,
            "linkFrom": {
                "resourceIri": "urn:archive:unit",
                "property": "shared:hasMediaObject",
                "replace": True,
            },
        },
        headers=token_headers[1],
    )

    assert missing_property.status_code == 400
    assert missing_property.json == {"message": "linkFrom.property is required."}
    assert unknown_field.status_code == 400
    assert "Unknown linkFrom field" in unknown_field.json["message"]
