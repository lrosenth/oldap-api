"""Offline safety checks for the production read measurement boundary."""
import unittest
from unittest.mock import patch

import requests
import read_vm as vm


class VmReadTest(unittest.TestCase):
    def setUp(self):
        self.api = "http://172.18.0.9:8000"
        self.case = {"id": "search", "method": "POST", "path": "/data/search/fasnacht",
                     "body": {"resClass": "fasnacht:ArchiveMediaObject", "limit": 25}}

    def test_mutation_and_ambiguous_paths_rejected(self):
        for method, path in (("DELETE", "/data/fasnacht/x"),
                             ("POST", "/data/fasnacht/x"),
                             ("GET", "/data/fasnacht/../../admin/users"),
                             ("GET", "https://external.invalid/data/fasnacht/x"),
                             ("POST", "/admin/auth/login")):
            with self.subTest(method=method, path=path), self.assertRaises(ValueError):
                vm.validate_case({"method": method, "path": path, "body": {}})

    def test_exact_request_boundary_and_redirects(self):
        with vm.ReadSession(self.api, [self.case]) as session:
            with patch.object(requests.Session, "request") as transport:
                session.post(self.api + self.case["path"], json=self.case["body"], allow_redirects=True)
                self.assertFalse(transport.call_args.kwargs["allow_redirects"])
                self.assertFalse(session.trust_env)
                transport.reset_mock()
                for method, url, body in (
                    ("DELETE", self.api + self.case["path"], self.case["body"]),
                    ("POST", "https://external.invalid" + self.case["path"], self.case["body"]),
                    ("POST", self.api + self.case["path"], {"limit": 999999}),
                ):
                    with self.assertRaises(RuntimeError):
                        session.request(method, url, json=body)
                transport.assert_not_called()

    def test_fingerprint_is_fixed_select_without_inference(self):
        with patch.object(requests.Session, "post") as post:
            post.return_value.json.return_value = {"results": {"bindings": []}}
            result = vm.fingerprint("http://localhost:7200")
            self.assertEqual(result["bindings"], 0)
            self.assertEqual(post.call_args.kwargs["data"], {
                "query": "SELECT ?g ?s ?p ?o WHERE { GRAPH ?g { ?s ?p ?o } }",
                "infer": "false", "timeout": "15",
            })
            self.assertFalse(post.call_args.kwargs["allow_redirects"])

    def test_process_replacement_stops_measurement(self):
        with patch.object(vm, "process_ids", return_value={"api_2": 2}):
            with self.assertRaisesRegex(RuntimeError, "identities changed"):
                vm.process_snapshot({"api_1": 1})

    def test_inventory_ignores_transient_helpers_but_keeps_all_workers(self):
        listings = ["PID COMMAND\n10 gunicorn\n11 gunicorn\n12 gunicorn\n90 curl\n91 python\n",
                    "PID COMMAND\n20 java\n92 sh\n", "PID COMMAND\n30 redis-server\n"]
        with patch.object(vm.subprocess, "check_output", side_effect=listings):
            actual = vm.process_ids()
        self.assertEqual(actual, {"load_client": vm.os.getpid(), "api_10": 10,
                                  "api_11": 11, "api_12": 12,
                                  "graphdb_20": 20, "redis_30": 30})

    def test_inventory_refuses_missing_service_processes(self):
        with patch.object(vm.subprocess, "check_output", return_value="PID COMMAND\n90 curl\n"):
            with self.assertRaisesRegex(RuntimeError, "No expected gunicorn"):
                vm.process_ids()

    def test_summary_count_measures_resources_not_wrapper_keys(self):
        with vm.ReadSession(self.api, [self.case]) as session:
            with patch.object(session, "request") as request:
                response = request.return_value
                response.json.return_value = {"resources": [{"iri": "a"}, {"iri": "b"}]}
                response.content = b"{}"
                response.status_code = 200
                result = vm.read_case(session, self.api, self.case)
                self.assertEqual(result["resources"], 2)
                self.assertEqual(result["items"], 1)


if __name__ == "__main__":
    unittest.main()
