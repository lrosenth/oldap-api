"""GraphDB target-child inspection tests for ZIP import preflight."""

import pytest
from rdflib import URIRef

from oldap_api.imports.authorization import (
    ImportTargetNotFoundError,
    OldapImportTargetInspector,
    _target_query,
)
from oldap_api.imports.domain import TargetSnapshot


class FakeConnection:
    """Return fixed SPARQL bindings while retaining the generated query."""

    def __init__(self, bindings):
        self.bindings = bindings
        self.query_text = None

    def query(self, query):
        self.query_text = query
        return {"results": {"bindings": self.bindings}}


def _target() -> TargetSnapshot:
    return TargetSnapshot(
        project_short_name="fasnacht",
        staging_area_iri="https://example.org/staging/area",
        staging_area_name="Area",
        target_root_folder_iri="https://example.org/staging/root",
        target_root_folder_name="Root",
    )


def test_public_target_query_is_self_contained_for_real_oldap_identifiers() -> None:
    """Public access-token requests must not depend on a QName context."""

    query = _target_query(
        "<urn:uuid:e70b3704-fed6-45a7-9d39-7c58f211ea7f>",
        URIRef("http://fasnacht.digital/ns/data"),
        "urn:uuid:e1c03947-4f53-465f-85c5-0296e12bd0cc",
        "urn:uuid:30aba28d-e931-48e9-bfd8-230f9e147f23",
    )

    assert "GRAPH <http://fasnacht.digital/ns/data>" in query
    assert "fasnacht:data" not in query
    assert "PREFIX schema: <https://schema.org/>" in query
    assert "rdfs:subClassOf+ shared:StagingArea" in query


def test_inspector_returns_current_snapshot_and_named_direct_children() -> None:
    connection = FakeConnection(
        [
            {
                "areaName": {"value": "Area"},
                "folderName": {"value": "Root"},
                "child": {"value": "https://example.org/staging/photos"},
                "kind": {"value": "http://oldap.org/shared#StagingFolder"},
                "name": {"value": "Photos"},
            },
            {
                "areaName": {"value": "Area"},
                "folderName": {"value": "Root"},
                "child": {"value": "https://example.org/staging/media"},
                "kind": {"value": "http://oldap.org/shared#StagingMediaObject"},
                "name": {"value": "image.jpg"},
            },
        ]
    )

    result = OldapImportTargetInspector(
        connection,
        data_graph_resolver=lambda _connection, _short_name: URIRef(
            "https://fasnacht.digital/data"
        ),
    ).inspect_target(_target())

    assert result.snapshot == _target()
    assert [(child.kind, child.name) for child in result.children] == [
        ("folder", "Photos"),
        ("media", "image.jpg"),
    ]
    assert "shared:inStagingFolder" in connection.query_text
    assert "GRAPH <https://fasnacht.digital/data>" in connection.query_text
    assert "fasnacht:data" not in connection.query_text
    assert "PREFIX schema: <https://schema.org/>" in connection.query_text
    assert "rdfs:subClassOf+ shared:StagingArea" in connection.query_text
    assert "LIMIT 10002" in connection.query_text


def test_inspector_rejects_a_missing_target() -> None:
    with pytest.raises(ImportTargetNotFoundError):
        OldapImportTargetInspector(
            FakeConnection([]),
            data_graph_resolver=lambda _connection, _short_name: URIRef(
                "https://fasnacht.digital/data"
            ),
        ).inspect_target(_target())
