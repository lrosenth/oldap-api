"""HTTP v1 conformance tests without live application/database fixtures."""

import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from flask import Flask
from jsonschema import Draft202012Validator

from oldap_api.views import archive_structure_views as views
from oldaplib.src.archive_policy import ArchiveConflict
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.oldaperror import (
    OldapErrorNoPermission,
    OldapErrorNotFound,
    OldapErrorValue,
)
from oldaplib.src.mutation_gate import MutationGateUnavailable
from oldaplib.src.xsd.iri import Iri

SCHEMA = json.loads(
    (Path(__file__).parents[2] / "doc/archive_structure_v1.schema.json").read_text()
)


class ArchiveStructureViewsTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(views.archive_structure_bp)
        # Test the actual response adapters separately from already covered JWT
        # authentication. Keep the real blueprint's cache policy in place.
        for endpoint, handler in list(self.app.view_functions.items()):
            if endpoint.startswith("archive_structure."):
                self.app.view_functions[endpoint] = handler.__wrapped__
        self.client = self.app.test_client()
        self.operation_id = str(uuid4())
        self.result = {
            "operationId": self.operation_id,
            "state": "committed",
            "mediaIri": "urn:as02:test:media",
            "sourceFolderIri": "urn:as02:test:source",
            "targetFolderIri": "urn:as02:test:target",
            "sourceRevision": "a" * 64,
            "targetRevision": "b" * 64,
        }

    def validate(self, response, name, status):
        self.assertEqual(response.status_code, status, response.json)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        Draft202012Validator({**SCHEMA, "$ref": "#/$defs/" + name}).validate(
            response.json
        )

    def test_default_proposal_forwards_read_request_with_no_store(self):
        body = {"sourceFolderIri": "urn:test:source"}
        from unittest.mock import MagicMock

        repo = MagicMock()
        repo.default_proposal.return_value = {
            "folders": [],
            "suggestedPlan": {"newUnits": [], "mappings": []},
        }
        with (
            patch.object(views, "authenticated_connection", return_value=object()),
            patch("oldaplib.src.archive_adoption.ArchiveAdoption", return_value=repo),
        ):
            response = self.client.post(
                "/archive/test/structure/defaults/proposal", json=body
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        repo.default_proposal.assert_called_once_with(body)

    def test_move_forwards_closed_request_and_idempotency_header(self):
        body = {
            key: value
            for key, value in self.result.items()
            if key not in {"operationId", "state"}
        }
        repo = SimpleNamespace(
            move_reference=lambda data, operation_id: (
                self.result
                if data == body and operation_id == self.operation_id
                else None
            )
        )
        with (
            patch.object(views, "authenticated_connection", return_value=object()),
            patch.object(views, "ArchiveRepository", return_value=repo),
        ):
            response = self.client.post(
                "/data/test/staging-reference-move",
                json=body,
                headers={"Idempotency-Key": self.operation_id},
            )
        self.validate(response, "ReferenceMoveResponse", 200)

    def test_typed_errors_follow_frozen_error_schema(self):
        stale = ArchiveConflict("reload")
        stale.code = "STALE_FOLDER"
        for error, status, code in (
            (OldapErrorNoPermission("private"), 403, "FORBIDDEN"),
            (OldapErrorNotFound("private"), 404, "NOT_FOUND"),
            (OldapErrorValue("bad"), 400, "INVALID_REQUEST"),
            (RuntimeError("private transport detail"), 503, "COORDINATION_UNAVAILABLE"),
            (stale, 409, "STALE_FOLDER"),
            (
                MutationGateUnavailable("private topology"),
                503,
                "COORDINATION_UNAVAILABLE",
            ),
        ):
            with (
                self.subTest(code=code),
                patch.object(views, "authenticated_connection", return_value=object()),
                patch.object(views, "ArchiveRepository", side_effect=error),
            ):
                response = self.client.post(
                    "/data/test/staging-reference-move", json={}
                )
            self.validate(response, "Error", status)
            self.assertEqual(response.json["code"], code)
            self.assertNotIn("private", response.json["message"])

    def test_bad_json_and_oversize_rejected_before_domain_call(self):
        with patch.object(views, "ArchiveRepository") as repository:
            malformed = self.client.post(
                "/data/test/staging-reference-move",
                data="{broken",
                content_type="application/json",
            )
            oversized = self.client.post(
                "/data/test/staging-reference-move",
                data='"' + "x" * views.MAX_REQUEST_BYTES + '"',
                content_type="application/json",
            )
        repository.assert_not_called()
        self.validate(malformed, "Error", 400)
        self.validate(oversized, "Error", 413)

    def test_receipt_is_schema_conformant(self):
        repo = SimpleNamespace(operation=lambda key: self.result)
        with (
            patch.object(views, "authenticated_connection", return_value=object()),
            patch.object(views, "ArchiveRepository", return_value=repo),
        ):
            response = self.client.get(
                "/archive/test/structure/operations/" + self.operation_id
            )
        self.validate(response, "ReferenceMoveResponse", 200)

    def test_capabilities_combine_role_and_create_permission(self):
        project_iri = Iri("urn:as02:test:project")
        actor = SimpleNamespace(inProject={project_iri: set()})
        con = SimpleNamespace(userdata=actor)
        policy = SimpleNamespace(
            enabled=True,
            structure_roles=("role",),
            has_role=lambda roles: True,
            project=SimpleNamespace(projectIri=project_iri),
        )
        with (
            patch.object(views, "authenticated_connection", return_value=con),
            patch.object(views.ArchivePolicy, "load", return_value=policy),
        ):
            response = self.client.get("/archive/test/structure/capabilities")
            self.validate(response, "CapabilitiesResponse", 200)
            self.assertTrue(response.json["canManageStructure"])
            self.assertFalse(response.json["canCreateUnits"])
            actor.inProject[project_iri].add(AdminPermission.ADMIN_CREATE)
            response = self.client.get("/archive/test/structure/capabilities")
            self.assertTrue(response.json["canCreateUnits"])

    def test_inventory_forwards_paging_and_validates_frozen_response(self):
        result = {
            "folderIri": "urn:as03:folder",
            "revision": "a" * 64,
            "entries": [
                {
                    "kind": "archiveReference",
                    "mediaIri": "urn:as03:medium",
                    "title": "Photo",
                    "canDownloadOriginal": True,
                    "canEditMetadata": False,
                    "canMove": True,
                    "canDeleteMedia": False,
                }
            ],
            "nextCursor": None,
            "warnings": [],
        }
        with (
            patch.dict(os.environ, {"OLDAP_ACCESS_JWT_SECRET": "x" * 48}),
            patch.object(views, "authenticated_connection", return_value=object()),
            patch("oldaplib.src.archive_inventory.ArchiveInventory") as service,
        ):
            service.return_value.page.return_value = result
            response = self.client.get(
                "/data/test/staging-folder-inventory",
                query_string={
                    "folderIri": "urn:as03:folder",
                    "limit": "12",
                    "cursor": "signed-cursor",
                },
            )
            service.return_value.page.assert_called_once_with(
                "urn:as03:folder", limit=12, cursor="signed-cursor"
            )
        self.validate(response, "InventoryResponse", 200)

    def test_inventory_rejects_unknown_duplicate_and_noninteger_parameters(self):
        for query in (
            "folderIri=urn:test&extra=1",
            "folderIri=urn:test&folderIri=urn:other",
            "folderIri=urn:test&limit=1.5",
            "folderIri=urn:test&limit=" + "9" * 5000,
        ):
            with (
                self.subTest(query=query[:40]),
                patch("oldaplib.src.archive_inventory.ArchiveInventory") as service,
            ):
                response = self.client.get(
                    "/data/test/staging-folder-inventory?" + query
                )
                service.assert_not_called()
                self.validate(response, "Error", 400)

    def test_adoption_routes_forward_bodies_and_operation_key(self):
        for command in ("proposal", "preflight", "apply"):
            with (
                self.subTest(command=command),
                patch.object(views, "authenticated_connection", return_value=object()),
                patch("oldaplib.src.archive_adoption.ArchiveAdoption") as service,
            ):
                getattr(service.return_value, command).return_value = {
                    "forwarded": True
                }
                body = {"request": command}
                response = self.client.post(
                    "/archive/test/structure/" + command,
                    json=body,
                    headers={"Idempotency-Key": self.operation_id},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                kwargs = (
                    {"operation_id": self.operation_id} if command == "apply" else {}
                )
                getattr(service.return_value, command).assert_called_once_with(
                    body, **kwargs
                )

    def test_adoption_body_limits_and_authentication(self):
        app = Flask("adoption_auth")
        app.register_blueprint(views.archive_structure_bp)
        for command in ("proposal", "preflight", "apply"):
            url = "/archive/test/structure/" + command
            self.assertEqual(app.test_client().post(url, json={}).status_code, 401)
            for data, status in (
                ("{broken", 400),
                ("[]", 400),
                ('"' + "x" * views.MAX_REQUEST_BYTES + '"', 413),
            ):
                with patch("oldaplib.src.archive_adoption.ArchiveAdoption") as service:
                    response = self.client.post(
                        url, data=data, content_type="application/json"
                    )
                    service.assert_not_called()
                    self.validate(response, "Error", status)

    def test_new_routes_still_require_authentication(self):
        app = Flask("authenticated")
        app.register_blueprint(views.archive_structure_bp)
        response = app.test_client().get("/archive/test/structure/capabilities")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(set(response.json), {"message"})
        self.assertEqual(response.headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
