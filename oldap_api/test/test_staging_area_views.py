"""HTTP-boundary regression tests for Step 11B Staging operations."""

from __future__ import annotations

from types import SimpleNamespace

from flask import Flask
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
import pytest

from oldap_api.staging_area import (
    DeletionTarget,
    StagingStructureConflict,
)
from oldap_api.views import instance_views
from oldap_api.views import import_views
from oldap_api.views import resource_views

AREA = "urn:uuid:00000000-0000-0000-0000-000000000301"
TOP = "urn:uuid:00000000-0000-0000-0000-000000000302"
MOBILE = "urn:uuid:00000000-0000-0000-0000-000000000303"
TRASH = "urn:uuid:00000000-0000-0000-0000-000000000304"
USER_FOLDER = "urn:uuid:00000000-0000-0000-0000-000000000305"


@pytest.fixture(autouse=True)
def immediate_staging_mutations(monkeypatch):
    """Keep route tests independent from the Redis integration boundary."""

    monkeypatch.setattr(
        instance_views,
        "run_staging_mutation",
        lambda resource_classes, operation: operation(),
    )


def test_dedicated_delete_delegates_to_one_atomic_repository_call(monkeypatch) -> None:
    calls = []

    class FakeRepository:
        def __init__(self, connection, project):
            calls.append((connection, project))

        def delete_empty(self, staging_area_iri):
            calls.append(staging_area_iri)
            return DeletionTarget(AREA, TOP, MOBILE, TRASH)

    connection = object()
    monkeypatch.setattr(instance_views, "authenticated_connection", lambda: connection)
    monkeypatch.setattr(instance_views, "GraphDbStagingAreaRepository", FakeRepository)
    app = Flask(__name__)

    with app.test_request_context(
        f"/data/fasnacht/{AREA}/staging-area", method="DELETE"
    ):
        response, status = instance_views.delete_empty_staging_area.__wrapped__(
            "fasnacht", AREA
        )

    assert status == 200
    assert response.get_json() == {
        "message": "StagingArea successfully deleted",
        "stagingAreaIri": AREA,
    }
    assert calls == [(connection, "fasnacht"), AREA]


def test_dedicated_delete_maps_validation_conflict_without_generic_fallback(
    monkeypatch,
) -> None:
    class FakeRepository:
        def __init__(self, connection, project):
            pass

        def delete_empty(self, staging_area_iri):
            raise StagingStructureConflict("The StagingArea is not empty.")

    monkeypatch.setattr(instance_views, "authenticated_connection", object)
    monkeypatch.setattr(instance_views, "GraphDbStagingAreaRepository", FakeRepository)
    app = Flask(__name__)

    with app.test_request_context(
        f"/data/fasnacht/{AREA}/staging-area", method="DELETE"
    ):
        response, status = instance_views.delete_empty_staging_area.__wrapped__(
            "fasnacht", AREA
        )

    assert status == 409
    assert response.get_json() == {"message": "The StagingArea is not empty."}


def test_generic_staging_move_stops_before_oldaplib_when_policy_rejects(
    monkeypatch,
) -> None:
    calls = []

    class RejectingPolicy:
        def __init__(self, connection, project):
            calls.append((connection, project))

        def assert_move_allowed(self, folder_iri, target_iri):
            calls.append((folder_iri, target_iri))
            raise StagingStructureConflict("The protected inbox cannot be moved.")

    class ForbiddenTree:
        def __init__(self, *args, **kwargs):
            raise AssertionError("oldaplib must not receive a rejected move")

    connection = SimpleNamespace(context_name="DEFAULT")
    Context(name="DEFAULT")["fasnacht"] = "http://oldap.org/fasnacht#"
    monkeypatch.setattr(instance_views, "authenticated_connection", lambda: connection)
    monkeypatch.setattr(instance_views, "StagingSystemFolderPolicy", RejectingPolicy)
    monkeypatch.setattr(instance_views, "StagingFolderTree", ForbiddenTree)
    app = Flask(__name__)
    target = "urn:uuid:00000000-0000-0000-0000-000000000305"

    with app.test_request_context(
        f"/data/fasnacht/{MOBILE}/staging-folder-move",
        method="POST",
        json={"shared:inStagingFolder": target},
    ):
        response, status = instance_views.move_staging_folder.__wrapped__(
            "fasnacht", MOBILE
        )

    assert status == 409
    assert response.get_json() == {"message": "The protected inbox cannot be moved."}
    assert calls == [(connection, "fasnacht"), (MOBILE, target)]


def test_generic_nonfolder_creation_retains_existing_path(monkeypatch) -> None:
    calls = []

    class RecordingPolicy:
        def __init__(self, connection, project):
            raise AssertionError(
                "ordinary resources must not initialize Staging policy"
            )

        def assert_create_allowed(self, resource_class, data):
            calls.append((resource_class, data))

    class FakeInstance:
        iri = Iri("urn:uuid:00000000-0000-0000-0000-000000000306")

        def create(self):
            calls.append("created")

    class FakeFactory:
        def __init__(self, con, project):
            pass

        def createObjectInstance(self, resource):
            return lambda **data: FakeInstance()

    monkeypatch.setattr(instance_views, "authenticated_connection", object)
    monkeypatch.setattr(instance_views, "StagingSystemFolderPolicy", RecordingPolicy)
    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", FakeFactory)
    app = Flask(__name__)
    payload = {"schema:name": ["Ordinary resource"]}

    with app.test_request_context(
        "/data/fasnacht/fasnacht:Place", method="PUT", json=payload
    ):
        response, status = instance_views.add_instance.__wrapped__(
            "fasnacht", "fasnacht:Place"
        )

    assert status == 200
    assert response.get_json()["iri"] == str(FakeInstance.iri)
    assert calls == ["created"]


def test_generic_staging_creation_checks_policy_inside_serialized_write(
    monkeypatch,
) -> None:
    calls = []

    class RecordingPolicy:
        def __init__(self, connection, project):
            pass

        def assert_create_allowed(self, resource_class, data):
            calls.append("policy")

    class FakeInstance:
        iri = Iri("urn:uuid:00000000-0000-0000-0000-000000000307")

        def create(self):
            calls.append("create")

    class FakeFactory:
        def __init__(self, con, project):
            pass

        def createObjectInstance(self, resource):
            return lambda **data: FakeInstance()

    def serialized(resource_classes, operation):
        calls.append(("lock", resource_classes))
        return operation()

    monkeypatch.setattr(instance_views, "authenticated_connection", object)
    monkeypatch.setattr(instance_views, "StagingSystemFolderPolicy", RecordingPolicy)
    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", FakeFactory)
    monkeypatch.setattr(instance_views, "run_staging_mutation", serialized)
    app = Flask(__name__)
    payload = {
        "schema:name": ["Mobile"],
        "shared:inStagingArea": [AREA],
        "shared:inStagingFolder": [TOP],
    }

    with app.test_request_context(
        "/data/fasnacht/shared:StagingFolder", method="PUT", json=payload
    ):
        response, status = instance_views.add_instance.__wrapped__(
            "fasnacht", "shared:StagingFolder"
        )

    assert status == 200
    assert response.get_json()["iri"] == str(FakeInstance.iri)
    assert calls == [
        ("lock", "shared:StagingFolder"),
        "policy",
        "create",
    ]


def test_generic_staging_update_checks_policy_inside_serialized_write(
    monkeypatch,
) -> None:
    calls = []

    class RecordingPolicy:
        def __init__(self, connection, project):
            pass

        def assert_update_allowed(self, folder_iri, data):
            calls.append("policy")

    class FakeInstance:
        name = Xsd_QName("shared:StagingFolder", validate=False)

        def __setitem__(self, key, value):
            calls.append("payload")

        def update(self):
            calls.append("update")

    class FakeFactory:
        def __init__(self, con, project):
            self.reads = 0

        def read(self, iri):
            self.reads += 1
            calls.append(f"read-{self.reads}")
            return FakeInstance()

    def serialized(resource_classes, operation):
        calls.append(("lock", str(resource_classes)))
        return operation()

    connection = SimpleNamespace(context_name="DEFAULT")
    Context(name="DEFAULT")["fasnacht"] = "http://oldap.org/fasnacht#"
    monkeypatch.setattr(instance_views, "authenticated_connection", lambda: connection)
    monkeypatch.setattr(instance_views, "StagingSystemFolderPolicy", RecordingPolicy)
    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", FakeFactory)
    monkeypatch.setattr(instance_views, "run_staging_mutation", serialized)
    app = Flask(__name__)

    with app.test_request_context(
        f"/data/fasnacht/{USER_FOLDER}",
        method="POST",
        json={"schema:name": ["Photos"]},
    ):
        response, status = instance_views.update_instance.__wrapped__(
            "fasnacht", USER_FOLDER
        )

    assert status == 200
    assert response.get_json() == {"message": "Instance successfully updated"}
    assert calls == [
        "read-1",
        ("lock", "shared:StagingFolder"),
        "read-2",
        "payload",
        "policy",
        "update",
    ]


def test_generic_staging_transform_uses_a_fresh_instance_inside_the_lock(
    monkeypatch,
) -> None:
    calls = []

    class RecordingPolicy:
        def __init__(self, connection, project):
            pass

        def assert_staging_area_transform_allowed(self, resource_class):
            calls.append("area-policy")

        def assert_transform_allowed(self, folder_iri):
            calls.append("folder-policy")

        def assert_transform_target_allowed(self, target_class):
            calls.append("target-policy")

    class FakeInstance:
        name = Xsd_QName("shared:StagingFolder", validate=False)

        def __init__(self, generation):
            self.generation = generation

        def transform_class(self, target_class, **kwargs):
            calls.append(f"transform-{self.generation}")
            return SimpleNamespace(
                iri=Iri(USER_FOLDER),
                name=Xsd_QName(target_class, validate=False),
            )

    class FakeFactory:
        def __init__(self, con, project):
            self.reads = 0

        def read(self, iri):
            self.reads += 1
            calls.append(f"read-{self.reads}")
            return FakeInstance(self.reads)

    def serialized(resource_classes, operation):
        calls.append(("lock", tuple(str(value) for value in resource_classes)))
        return operation()

    connection = SimpleNamespace(context_name="DEFAULT")
    Context(name="DEFAULT")["fasnacht"] = "http://oldap.org/fasnacht#"
    monkeypatch.setattr(instance_views, "authenticated_connection", lambda: connection)
    monkeypatch.setattr(instance_views, "StagingSystemFolderPolicy", RecordingPolicy)
    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", FakeFactory)
    monkeypatch.setattr(instance_views, "run_staging_mutation", serialized)
    app = Flask(__name__)

    with app.test_request_context(
        f"/data/fasnacht/{USER_FOLDER}/transform",
        method="POST",
        json={
            "targetClass": "fasnacht:Place",
            "preserveClass": "shared:StagingFolder",
        },
    ):
        response, status = instance_views.transform_instance.__wrapped__(
            "fasnacht", USER_FOLDER
        )

    assert status == 200
    assert response.get_json()["resourceClass"] == "fasnacht:Place"
    assert calls == [
        "read-1",
        ("lock", ("shared:StagingFolder", "fasnacht:Place")),
        "read-2",
        "area-policy",
        "folder-policy",
        "target-policy",
        "transform-2",
    ]


def test_generic_staging_area_delete_requires_the_atomic_route(monkeypatch) -> None:
    calls = []

    class RejectingPolicy:
        def __init__(self, connection, project):
            pass

        def assert_staging_area_delete_allowed(self, resource_class):
            calls.append("policy")
            raise StagingStructureConflict("Use the atomic StagingArea operation.")

    class FakeInstance:
        name = Xsd_QName("fasnacht:StagingArea", validate=False)

        def delete(self):
            raise AssertionError("Generic deletion must not reach oldaplib")

    class FakeFactory:
        def __init__(self, con, project):
            self.reads = 0

        def read(self, iri):
            self.reads += 1
            calls.append(f"read-{self.reads}")
            return FakeInstance()

    def serialized(resource_classes, operation):
        calls.append(("lock", str(resource_classes)))
        return operation()

    connection = SimpleNamespace(context_name="DEFAULT")
    Context(name="DEFAULT")["fasnacht"] = "http://oldap.org/fasnacht#"
    monkeypatch.setattr(instance_views, "authenticated_connection", lambda: connection)
    monkeypatch.setattr(instance_views, "StagingSystemFolderPolicy", RejectingPolicy)
    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", FakeFactory)
    monkeypatch.setattr(instance_views, "run_staging_mutation", serialized)
    app = Flask(__name__)

    with app.test_request_context(
        f"/data/fasnacht/{AREA}",
        method="DELETE",
    ):
        response, status = instance_views.delete_instance.__wrapped__("fasnacht", AREA)

    assert status == 409
    assert response.get_json() == {"message": "Use the atomic StagingArea operation."}
    assert calls == [
        "read-1",
        ("lock", "fasnacht:StagingArea"),
        "read-2",
        "policy",
    ]


def test_stale_staging_delete_cannot_delete_a_concurrently_transformed_resource(
    monkeypatch,
) -> None:
    calls = []

    class FakeInstance:
        def __init__(self, resource_class):
            self.name = Xsd_QName(resource_class, validate=False)

        def delete(self):
            calls.append("delete")

    class FakeFactory:
        def __init__(self, con, project):
            self.instances = iter(
                (
                    FakeInstance("shared:StagingMediaObject"),
                    FakeInstance("fasnacht:ArchiveMediaObject"),
                )
            )

        def read(self, iri):
            instance = next(self.instances)
            calls.append(str(instance.name))
            return instance

    def serialized(resource_classes, operation):
        calls.append(("lock", str(resource_classes)))
        return operation()

    connection = SimpleNamespace(context_name="DEFAULT")
    Context(name="DEFAULT")["fasnacht"] = "http://oldap.org/fasnacht#"
    monkeypatch.setattr(instance_views, "authenticated_connection", lambda: connection)
    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", FakeFactory)
    monkeypatch.setattr(instance_views, "run_staging_mutation", serialized)
    app = Flask(__name__)

    with app.test_request_context(
        f"/data/fasnacht/{USER_FOLDER}",
        method="DELETE",
    ):
        response, status = instance_views.delete_instance.__wrapped__(
            "fasnacht", USER_FOLDER
        )

    assert status == 409
    assert response.get_json() == {
        "message": "The resource class changed while the Staging operation was waiting."
    }
    assert calls == [
        "shared:StagingMediaObject",
        ("lock", "shared:StagingMediaObject"),
        "fasnacht:ArchiveMediaObject",
    ]


def test_legacy_admin_create_cannot_bypass_staging_policy(monkeypatch) -> None:
    calls = []

    class FakeProject:
        @staticmethod
        def read(*, con, projectIri_SName):
            return SimpleNamespace(projectShortName=projectIri_SName)

    class FakeDataModel:
        @staticmethod
        def read(con, project, ignore_cache=True):
            return object()

    class FakeInstance:
        iri = Iri("urn:uuid:00000000-0000-0000-0000-000000000308")

        def create(self):
            calls.append("create")

    class FakeFactory:
        def __init__(self, con, project):
            pass

        def createObjectInstance(self, resource):
            return lambda **data: FakeInstance()

    class RejectingPolicy:
        def __init__(self, connection, project):
            calls.append(("policy-context", project))

        def assert_create_allowed(self, resource_class, data):
            calls.append(("policy", resource_class))
            if resource_class == "shared:StagingFolder":
                raise StagingStructureConflict("Reserved Staging folder rejected.")

    def serialized(resource_classes, operation):
        calls.append(("lock", resource_classes))
        return operation()

    monkeypatch.setattr(resource_views, "authenticated_connection", object)
    monkeypatch.setattr(resource_views, "Project", FakeProject)
    monkeypatch.setattr(resource_views, "DataModel", FakeDataModel)
    monkeypatch.setattr(resource_views, "ResourceInstanceFactory", FakeFactory)
    monkeypatch.setattr(resource_views, "StagingSystemFolderPolicy", RejectingPolicy)
    monkeypatch.setattr(resource_views, "run_staging_mutation", serialized)
    app = Flask(__name__)

    with app.test_request_context(
        "/admin/fasnacht/shared:StagingFolder",
        method="PUT",
        json={"schema:name": ["Mobile"]},
    ):
        response, status = resource_views.create_resource.__wrapped__(
            "fasnacht", "shared:StagingFolder"
        )

    assert status == 409
    assert response.get_json() == {"message": "Reserved Staging folder rejected."}
    assert calls == [
        ("lock", "shared:StagingFolder"),
        ("policy-context", "fasnacht"),
        ("policy", "shared:StagingFolder"),
    ]

    calls.clear()
    with app.test_request_context(
        "/admin/fasnacht/fasnacht:Place",
        method="PUT",
        json={"schema:name": ["Ordinary resource"]},
    ):
        response, status = resource_views.create_resource.__wrapped__(
            "fasnacht", "fasnacht:Place"
        )

    assert status == 200
    assert response.get_json() == {"message": "OK", "iri": str(FakeInstance.iri)}
    assert calls == [("lock", "fasnacht:Place"), "create"]


def test_zip_import_commit_uses_the_shared_staging_write_lease(monkeypatch) -> None:
    calls = []
    job = SimpleNamespace(to_dict=lambda: {"state": "IMPORTED"})

    class FakeService:
        def commit_import(self, import_id, payload):
            calls.append(("commit", import_id, payload))
            return job, "event-id", ({"iri": "urn:uuid:resource"},)

    def serialized(resource_classes, operation):
        calls.append(("lock", resource_classes))
        return operation()

    monkeypatch.setattr(import_views, "_internal_service", FakeService)
    monkeypatch.setattr(import_views, "run_staging_mutation", serialized)
    monkeypatch.setattr(
        import_views, "_attempt_notification", lambda service, value: value
    )
    monkeypatch.setattr(import_views, "log_import_event", lambda *args, **kwargs: None)
    app = Flask(__name__)
    payload = {"eventId": "event-id"}

    with app.test_request_context(
        "/internal/imports/import-id/commit", method="POST", json=payload
    ):
        response = import_views.commit_staging_import.__wrapped__("import-id")

    assert response.get_json() == {
        "eventId": "event-id",
        "job": {"state": "IMPORTED"},
        "resources": [{"iri": "urn:uuid:resource"}],
    }
    assert calls == [
        ("lock", "shared:StagingMediaObject"),
        ("commit", "import-id", payload),
    ]
