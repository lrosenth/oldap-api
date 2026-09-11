"""Verify archive endpoint dispatch alongside the generic production data routes."""

import unittest

from oldap_api.factory import factory


class ArchiveRouteDispatchTest(unittest.TestCase):
    """Exercise the complete route map without initializing external services."""

    @classmethod
    def setUpClass(cls):
        cls.app = factory()

    def test_archive_data_endpoints_win_over_instance_routes(self):
        adapter = self.app.url_map.bind("localhost")
        for project in ("fasnacht", "https://fasnacht.digital"):
            for suffix, method, handler in (
                ("staging-folder-inventory", "GET", "folder_inventory"),
                ("staging-reference-move", "POST", "move_reference"),
            ):
                with self.subTest(project=project, suffix=suffix):
                    endpoint, values = adapter.match(
                        f"/data/{project}/{suffix}", method=method
                    )
                    self.assertEqual(endpoint, f"archive_structure.{handler}")
                    self.assertEqual(values, {"project": project})

    def test_ordinary_instance_reads_keep_their_route(self):
        adapter = self.app.url_map.bind("localhost")
        for iri in ("urn:uuid:example", "https://example.org/media/1"):
            with self.subTest(iri=iri):
                endpoint, values = adapter.match(f"/data/fasnacht/{iri}", method="GET")
                self.assertEqual(endpoint, "instance.read_instance")
                self.assertEqual(values, {"project": "fasnacht", "instiri": iri})

    def test_inventory_still_requires_authentication(self):
        response = self.app.test_client().get(
            "/data/fasnacht/staging-folder-inventory?folderIri=urn:uuid:example&limit=100"
        )
        self.assertEqual(response.status_code, 401)
