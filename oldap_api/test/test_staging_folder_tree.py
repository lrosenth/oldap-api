"""HTTP contract tests for safe shared Staging folder moves."""

from types import SimpleNamespace

from oldap_api.views import instance_views
from oldaplib.src.helpers.oldaperror import (
    OldapErrorAlreadyExists,
    OldapErrorInconsistency,
)
from oldaplib.src.xsd.iri import Iri


def test_move_staging_folder_delegates_to_oldaplib(client, token_headers, monkeypatch):
    """The endpoint delegates the explicit parent relation to oldaplib."""
    calls = {}
    node_iri = "urn:uuid:00000000-0000-0000-0000-000000000110"
    parent_iri = "urn:uuid:00000000-0000-0000-0000-000000000111"

    class FakeStagingFolderTree:
        def __init__(self, con, project):
            calls["project"] = project
            calls["connection"] = con

        def move(self, folder, parent_folder):
            calls["move"] = (folder, parent_folder)
            return SimpleNamespace(
                iri=Iri(node_iri),
                get=lambda key: {Iri(parent_iri)} if str(key) == "shared:inStagingFolder" else None,
            )

    monkeypatch.setattr(instance_views, "StagingFolderTree", FakeStagingFolderTree)
    response = client.post(
        f"/data/test/{node_iri}/staging-folder-move",
        json={"shared:inStagingFolder": parent_iri},
        headers=token_headers[1],
    )

    assert response.status_code == 200
    assert response.json == {
        "message": "Staging folder successfully moved",
        "iri": node_iri,
        "shared:inStagingFolder": parent_iri,
    }
    assert calls["project"] == "test"
    assert calls["move"] == (Iri(node_iri), parent_iri)


def test_move_staging_folder_maps_integrity_conflicts(client, token_headers, monkeypatch):
    """Cycles and sibling collisions use a stable HTTP conflict response."""
    node_iri = "urn:uuid:00000000-0000-0000-0000-000000000120"

    class FakeStagingFolderTree:
        error = OldapErrorInconsistency("The move would create a cycle.")

        def __init__(self, con, project):
            pass

        def move(self, folder, parent_folder):
            raise self.error

    monkeypatch.setattr(instance_views, "StagingFolderTree", FakeStagingFolderTree)
    cycle = client.post(
        f"/data/test/{node_iri}/staging-folder-move",
        json={"shared:inStagingFolder": node_iri},
        headers=token_headers[1],
    )
    FakeStagingFolderTree.error = OldapErrorAlreadyExists("Folder name already exists.")
    collision = client.post(
        f"/data/test/{node_iri}/staging-folder-move",
        json={"shared:inStagingFolder": "urn:uuid:00000000-0000-0000-0000-000000000121"},
        headers=token_headers[1],
    )

    assert cycle.status_code == 409
    assert collision.status_code == 409


def test_move_staging_folder_validates_payload(client, token_headers):
    """The endpoint requires exactly one non-empty parent IRI."""
    node_iri = "urn:uuid:00000000-0000-0000-0000-000000000130"
    header = token_headers[1]

    missing = client.post(
        f"/data/test/{node_iri}/staging-folder-move", json={}, headers=header
    )
    null_parent = client.post(
        f"/data/test/{node_iri}/staging-folder-move",
        json={"shared:inStagingFolder": None},
        headers=header,
    )

    assert missing.status_code == 400
    assert null_parent.status_code == 400


def test_generic_update_cannot_bypass_staging_folder_move(client, token_headers, monkeypatch):
    """The generic update endpoint cannot bypass Staging tree checks."""
    node_iri = "urn:uuid:00000000-0000-0000-0000-000000000140"

    class FakeFactory:
        def __init__(self, con, project):
            pass

        def read(self, iri):
            return SimpleNamespace(name=instance_views.Xsd_QName("shared:StagingFolder"))

    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", FakeFactory)
    response = client.post(
        f"/data/test/{node_iri}",
        json={
            "shared:inStagingFolder": "urn:uuid:00000000-0000-0000-0000-000000000141"
        },
        headers=token_headers[1],
    )

    assert response.status_code == 400
    assert response.json == {
        "message": (
            "Staging folder hierarchy must be changed through the "
            "staging-folder-move endpoint."
        )
    }
