"""HTTP contract tests for safe shared archive-unit moves."""

from types import SimpleNamespace

from oldap_api.views import instance_views
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_integer import Xsd_integer


def test_move_archive_unit_delegates_to_oldaplib(client, token_headers, monkeypatch):
    """The endpoint passes explicit ontology fields to the archive service."""
    calls = {}
    node_iri = "urn:uuid:00000000-0000-0000-0000-000000000010"
    parent_iri = "urn:uuid:00000000-0000-0000-0000-000000000011"

    class FakeArchiveTree:
        def __init__(self, con, project):
            calls["project"] = project
            calls["connection"] = con

        def move(self, archive_unit, parent_archive_unit, *, position):
            calls["move"] = (archive_unit, parent_archive_unit, position)
            values = {
                "shared:parentArchiveUnit": {Iri(parent_iri)},
                "schema:position": {Xsd_integer(3)},
            }
            return SimpleNamespace(
                iri=Iri(node_iri),
                get=lambda key: values.get(str(key)),
            )

    monkeypatch.setattr(instance_views, "ArchiveTree", FakeArchiveTree)
    response = client.post(
        f"/data/test/{node_iri}/archive-move",
        json={
            "shared:parentArchiveUnit": parent_iri,
            "schema:position": 3,
        },
        headers=token_headers[1],
    )

    assert response.status_code == 200
    assert response.json == {
        "message": "Archive unit successfully moved",
        "iri": node_iri,
        "shared:parentArchiveUnit": parent_iri,
        "schema:position": 3,
    }
    assert calls["project"] == "test"
    assert calls["move"] == (Iri(node_iri), parent_iri, 3)


def test_move_archive_unit_maps_cycle_to_conflict(client, token_headers, monkeypatch):
    """A cycle rejected by oldaplib is a stable HTTP conflict response."""
    node_iri = "urn:uuid:00000000-0000-0000-0000-000000000020"

    class FakeArchiveTree:
        def __init__(self, con, project):
            pass

        def move(self, archive_unit, parent_archive_unit, *, position):
            raise OldapErrorInconsistency("The move would create a cycle.")

    monkeypatch.setattr(instance_views, "ArchiveTree", FakeArchiveTree)
    response = client.post(
        f"/data/test/{node_iri}/archive-move",
        json={"shared:parentArchiveUnit": node_iri},
        headers=token_headers[1],
    )

    assert response.status_code == 409
    assert response.json == {"message": "The move would create a cycle."}


def test_move_archive_unit_validates_payload(client, token_headers):
    """The endpoint requires an explicit parent and a valid optional position."""
    node_iri = "urn:uuid:00000000-0000-0000-0000-000000000030"
    header = token_headers[1]

    missing_parent = client.post(
        f"/data/test/{node_iri}/archive-move",
        json={"schema:position": 1},
        headers=header,
    )
    invalid_position = client.post(
        f"/data/test/{node_iri}/archive-move",
        json={"shared:parentArchiveUnit": None, "schema:position": "first"},
        headers=header,
    )

    assert missing_parent.status_code == 400
    assert invalid_position.status_code == 400


def test_generic_update_cannot_bypass_archive_move(client, token_headers, monkeypatch):
    """Archive hierarchy fields use the dedicated cycle-safe mutation boundary."""
    node_iri = "urn:uuid:00000000-0000-0000-0000-000000000040"

    class FakeFactory:
        def __init__(self, con, project):
            pass

        def read(self, iri):
            return SimpleNamespace(name=instance_views.Xsd_QName("shared:ArchiveUnit"))

    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", FakeFactory)
    response = client.post(
        f"/data/test/{node_iri}",
        json={"shared:parentArchiveUnit": node_iri},
        headers=token_headers[1],
    )

    assert response.status_code == 400
    assert response.json == {
        "message": "Archive structure fields must be changed through the archive-move endpoint."
    }
