"""Isolated update-boundary regressions; no application/database fixtures."""

from contextlib import nullcontext
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask

from oldap_api.views import instance_views as views
from oldaplib.src.helpers.oldaperror import (
    OldapError,
    OldapErrorInUse,
    OldapErrorNoPermission,
    OldapErrorNotFound,
    OldapErrorValue,
)
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.archive_policy import PreparationNoteArchived


class FakeInstance:
    name = Xsd_QName("shared:MediaObject", validate=False)
    superclass = {}
    properties = {Xsd_QName("schema:comment"): SimpleNamespace(datatype=None)}

    def __init__(self, error=None):
        self.error = error
        self.updated = False
        self.values = {}

    def __setitem__(self, key, value):
        self.values[key] = value

    def __delitem__(self, key):
        self.values.pop(key, None)

    def get(self, key):
        return self.values.get(key)

    def update(self):
        if self.error:
            raise self.error
        self.updated = True


class ArchiveUpdateBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        # Authentication is outside this test's scope. Exercise the real route
        # body and real JSON serialization without loading destructive fixtures.
        self.app.add_url_rule(
            "/update",
            view_func=lambda: views.update_instance.__wrapped__(
                "shared", "urn:as02:medium"
            ),
            methods=["POST"],
        )
        self.client = self.app.test_client()
        self.connection = SimpleNamespace(context_name="AS02-api-tests")

    def send(self, payload, instance=None):
        instance = instance or FakeInstance()
        factory = SimpleNamespace(read=lambda iri: instance)
        with (
            patch.object(
                views, "authenticated_connection", return_value=self.connection
            ),
            patch.object(views, "ResourceInstanceFactory", return_value=factory),
        ):
            return self.client.post("/update", json=payload)

    def test_typed_errors_keep_legacy_message_envelope(self):
        for error, status in (
            (OldapErrorNoPermission("denied"), 403),
            (OldapErrorNotFound("missing"), 404),
            (OldapErrorValue("invalid"), 400),
            (OldapErrorInUse("referenced"), 409),
            (OldapError("unexpected"), 500),
        ):
            with self.subTest(status=status):
                response = self.send(
                    {"schema:comment": ["note@de"]}, FakeInstance(error)
                )
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json, {"message": str(error)})

    def test_archived_note_rejection_precedes_mobile_hook_and_payload_changes(self):
        for note in (["late@de"], None):
            instance = FakeInstance()
            instance.project = "shared"
            policy = SimpleNamespace(
                check_note_payload=Mock(side_effect=PreparationNoteArchived())
            )
            with (
                patch.object(views, "archive_coordination_enabled", return_value=True),
                patch.object(views, "resource_transaction", return_value=nullcontext()),
                patch.object(views, "archive_policy_for", return_value=policy),
                patch.object(views, "_mobile_lifecycle_hook") as hook,
            ):
                response = self.send({"schema:comment": note}, instance)
            self.assertEqual(response.status_code, 409)
            self.assertEqual(set(response.json), {"message"})
            self.assertFalse(instance.updated)
            self.assertEqual(instance.values, {})
            hook.assert_not_called()

    def test_non_object_body_rejected_before_factory(self):
        with patch.object(views, "ResourceInstanceFactory") as factory:
            response = self.client.post("/update", json=["invalid"])
        self.assertEqual(response.status_code, 400)
        factory.assert_not_called()

    def test_unknown_property_rejected_for_every_write_shape(self):
        for value in (["value"], None, {"add": ["value"]}, {"del": ["value"]}):
            with self.subTest(value=value):
                instance = FakeInstance()
                response = self.send({"schema:unknown": value}, instance)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(instance.updated)

    def test_absent_known_property_clear_remains_idempotent(self):
        for value in (None, {"del": ["de"]}):
            response = self.send({"schema:comment": value})
            self.assertEqual(response.status_code, 200)

    def test_archive_subclass_cannot_bypass_move_endpoint(self):
        class ProjectUnit(FakeInstance):
            name = Xsd_QName("project:SpecialUnit")
            superclass = {
                Xsd_QName("project:Unit"): SimpleNamespace(
                    superclass={
                        Xsd_QName("shared:ArchiveUnit"): SimpleNamespace(superclass={})
                    }
                )
            }

        instance = ProjectUnit()
        response = self.send({"shared:parentArchiveUnit": ["urn:parent"]}, instance)
        self.assertEqual(response.status_code, 400)
        self.assertIn("archive-move", response.json["message"])
        self.assertFalse(instance.updated)

    def test_folder_subclass_cannot_bypass_move_endpoint(self):
        class ProjectFolder(FakeInstance):
            name = Xsd_QName("project:Folder")
            superclass = {
                Xsd_QName("shared:StagingFolder"): SimpleNamespace(superclass={})
            }

        response = self.send(
            {"shared:inStagingFolder": ["urn:parent"]}, ProjectFolder()
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("staging-folder-move", response.json["message"])


if __name__ == "__main__":
    unittest.main()
