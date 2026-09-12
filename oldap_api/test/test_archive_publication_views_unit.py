"""Publication route dispatch, request forwarding and non-disclosing errors."""

import unittest
from unittest.mock import MagicMock, patch
from flask import Flask
from oldap_api.views import archive_publication_views as views
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission


class PublicationViewsTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(views.archive_publication_bp)
        for name, handler in list(self.app.view_functions.items()):
            if name.startswith("archive_publication."):
                self.app.view_functions[name] = handler.__wrapped__
        self.client = self.app.test_client()

    def test_all_endpoints_use_shared_service_and_no_store(self):
        service = MagicMock()
        service.capabilities.return_value = {"enabled": False, "canPublish": False}
        service.preview.return_value = {
            "revision": "a" * 64,
            "resources": [],
            "resourceIri": "urn:test:item",
        }
        service.apply.return_value = service.operation.return_value = {
            "state": "committed",
            "resourceIris": [],
            "operationId": "00000000-0000-4000-8000-000000000001",
        }
        with patch.object(
            views, "authenticated_connection", return_value=object()
        ), patch.object(views, "publication_service", return_value=service):
            for path, method, body in [
                ("capabilities?resourceIri=urn:test:item", "get", None),
                (
                    "preview",
                    "post",
                    {"resourceIri": "urn:test:item", "permission": "DATA_VIEW"},
                ),
                (
                    "apply",
                    "post",
                    {
                        "resourceIri": "urn:test:item",
                        "permission": "DATA_VIEW",
                        "revision": "a" * 64,
                    },
                ),
                ("operations/00000000-0000-4000-8000-000000000001", "get", None),
            ]:
                response = getattr(self.client, method)(
                    "/archive/museum/publication/" + path,
                    json=body,
                    headers={"Idempotency-Key": "00000000-0000-4000-8000-000000000001"},
                )
                self.assertEqual(response.status_code, 200, response.json)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
        service.capabilities.assert_called_once_with("urn:test:item")
        self.assertEqual(
            service.apply.call_args.args[1], "00000000-0000-4000-8000-000000000001"
        )

    def test_denied_dependencies_do_not_disclose_identity(self):
        service = MagicMock()
        service.preview.side_effect = OldapErrorNoPermission("urn:secret:item")
        with patch.object(
            views, "authenticated_connection", return_value=object()
        ), patch.object(views, "publication_service", return_value=service):
            response = self.client.post("/archive/museum/publication/preview", json={})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("urn:secret", response.text)

    def test_invalid_json_is_rejected(self):
        with patch.object(
            views, "authenticated_connection", return_value=object()
        ), patch.object(views, "publication_service"):
            response = self.client.post("/archive/museum/publication/preview", json=[])
        self.assertEqual(response.status_code, 400)

    def test_full_factory_authentication_and_dispatch(self):
        from oldap_api.factory import factory

        app = factory()
        adapter = app.url_map.bind("localhost")
        for suffix, method, endpoint in [
            ("capabilities", "GET", "capabilities"),
            ("preview", "POST", "preview"),
            ("apply", "POST", "apply"),
            ("operations/id", "GET", "operation"),
        ]:
            path = "/archive/museum/publication/" + suffix
            self.assertEqual(
                adapter.match(path, method=method)[0], "archive_publication." + endpoint
            )
            self.assertEqual(
                app.test_client().open(path, method=method).status_code, 401
            )
