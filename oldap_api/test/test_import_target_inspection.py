"""GraphDB target-child inspection tests for ZIP import preflight."""

from types import SimpleNamespace

import pytest
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.xsd.iri import Iri
from rdflib import URIRef

from oldap_api.imports.authorization import (
    ImportQuotaNotConfiguredError,
    ImportTargetProtectedError,
    ImportTargetNotFoundError,
    OldapImportAuthorizer,
    OldapImportTargetInspector,
    Project,
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
    assert "shared:mediaPath ?mediaPath" in query
    assert "shared:stagingDefaultRole ?defaultRole" in query
    assert "oldap:hasDataPermission ?defaultPermission" in query
    assert (
        "OPTIONAL { <urn:uuid:e1c03947-4f53-465f-85c5-0296e12bd0cc> shared:stagingQuotaBytes ?quota . }"
        in query
    )


def test_authorizer_returns_server_owned_upload_configuration(monkeypatch) -> None:
    """A valid target exposes only configuration derived from OLDAP data."""

    project_iri = Iri("https://example.org/project")
    project = SimpleNamespace(
        projectIri=project_iri,
        namespaceIri="https://example.org/project/",
    )
    monkeypatch.setattr(Project, "read", staticmethod(lambda **_kwargs: project))
    connection = FakeConnection(
        [
            {
                "areaName": {"value": "Chama Demo Staging"},
                "folderName": {"value": "Own photographs"},
                "quota": {"value": "10737418240"},
                "mediaPath": {"value": "chama"},
                "defaultRole": {"value": "https://example.org/project/Curator"},
                "defaultPermission": {
                    "value": "http://oldap.org/base#DATA_PERMISSIONS"
                },
            }
        ]
    )
    connection.userIri = Iri("https://example.org/users/alice")
    connection.userdata = SimpleNamespace(
        inProject={project_iri: {AdminPermission.ADMIN_CREATE}}
    )

    result = OldapImportAuthorizer().authorize_target(
        connection,
        project_short_name="chama",
        staging_area_iri="https://example.org/staging/area",
        target_root_folder_iri="https://example.org/staging/photos",
    )

    assert result.quota_limit_bytes == 10_737_418_240
    assert result.media_path == "chama"
    assert result.default_role_qname == "chama:Curator"
    assert result.default_permission == "DATA_PERMISSIONS"


def test_authorizer_expands_project_qnames_before_custom_sparql(monkeypatch) -> None:
    """Documented project QNames must resolve to their authoritative namespace."""

    project_iri = Iri("https://chama.salsah.org")
    project = SimpleNamespace(
        projectIri=project_iri,
        namespaceIri="https://chama.salsah.org/ns/",
    )
    monkeypatch.setattr(Project, "read", staticmethod(lambda **_kwargs: project))
    connection = FakeConnection(
        [
            {
                "areaName": {"value": "Chama Demo Staging"},
                "folderName": {"value": "Own photographs"},
                "quota": {"value": "10737418240"},
                "mediaPath": {"value": "chama"},
                "defaultRole": {"value": "https://chama.salsah.org/ns/Curator"},
                "defaultPermission": {
                    "value": "http://oldap.org/base#DATA_PERMISSIONS"
                },
            }
        ]
    )
    connection.userIri = Iri("https://example.org/users/alice")
    connection.userdata = SimpleNamespace(
        inProject={project_iri: {AdminPermission.ADMIN_CREATE}}
    )

    result = OldapImportAuthorizer().authorize_target(
        connection,
        project_short_name="chama",
        staging_area_iri="chama:ChamaDemoStaging",
        target_root_folder_iri="chama:ChamaOwnPhotographs",
    )

    assert "<https://chama.salsah.org/ns/ChamaDemoStaging>" in connection.query_text
    assert "<https://chama.salsah.org/ns/ChamaOwnPhotographs>" in connection.query_text
    assert "<chama:" not in connection.query_text
    assert (
        result.snapshot.staging_area_iri
        == "https://chama.salsah.org/ns/ChamaDemoStaging"
    )
    assert (
        result.snapshot.target_root_folder_iri
        == "https://chama.salsah.org/ns/ChamaOwnPhotographs"
    )


def test_authorizer_reports_a_missing_quota_after_finding_the_target(
    monkeypatch,
) -> None:
    """A restored pre-quota StagingArea must not be misreported as missing."""

    project_iri = Iri("https://example.org/project")
    project = SimpleNamespace(
        projectIri=project_iri,
        namespaceIri="https://example.org/project/",
    )
    monkeypatch.setattr(Project, "read", staticmethod(lambda **_kwargs: project))

    connection = FakeConnection(
        [
            {
                "areaName": {"value": "Restored area"},
                "folderName": {"value": "Root"},
            }
        ]
    )
    connection.userIri = Iri("https://example.org/users/alice")
    connection.userdata = SimpleNamespace(
        inProject={project_iri: {AdminPermission.ADMIN_CREATE}}
    )

    with pytest.raises(
        ImportQuotaNotConfiguredError,
        match="no shared:stagingQuotaBytes value",
    ):
        OldapImportAuthorizer().authorize_target(
            connection,
            project_short_name="fasnacht",
            staging_area_iri="https://example.org/staging/area",
            target_root_folder_iri="https://example.org/staging/root",
        )


def test_authorizer_rejects_the_protected_mobile_inbox(monkeypatch) -> None:
    project_iri = Iri("https://example.org/project")
    project = SimpleNamespace(
        projectIri=project_iri,
        namespaceIri="https://example.org/project/",
    )
    monkeypatch.setattr(Project, "read", staticmethod(lambda **_kwargs: project))
    connection = FakeConnection(
        [
            {
                "areaName": {"value": "Area"},
                "folderName": {"value": "Mobile"},
                "quota": {"value": "3000000000"},
            }
        ]
    )
    connection.userIri = Iri("https://example.org/users/alice")
    connection.userdata = SimpleNamespace(
        inProject={project_iri: {AdminPermission.ADMIN_CREATE}}
    )

    with pytest.raises(ImportTargetProtectedError):
        OldapImportAuthorizer().authorize_target(
            connection,
            project_short_name="fasnacht",
            staging_area_iri="https://example.org/staging/area",
            target_root_folder_iri="https://example.org/staging/mobile",
        )


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
