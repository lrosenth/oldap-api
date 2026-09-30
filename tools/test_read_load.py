"""Offline tests for load-test safety and measurement helpers."""
import unittest
from unittest.mock import patch
import requests
import read_load as load


class LoadTest(unittest.TestCase):
    def test_percentiles(self):
        self.assertEqual(load.stats(list(range(1, 101)))["p95_ms"], 95)
        self.assertEqual(load.stats([]), {"n": 0})

    def test_cpu_clock(self):
        self.assertEqual(load.cpu_seconds("01:02.50"), 62.5)
        self.assertEqual(load.cpu_seconds("1-02:03:04"), 93784)

    def test_response_equivalence(self):
        self.assertEqual(load.content_hash({"a": [2, 1], "capability": "x"}),
                         load.content_hash({"a": [1, 2], "capability": "y"}))
        self.assertNotEqual(load.content_hash({"iri": "a"}), load.content_hash({"iri": "b"}))

    def test_transport_rejects_mutation(self):
        original = requests.sessions.Session.request
        try:
            load.baseline.install_transport_guard(load.baseline.Recorder())
            with self.assertRaises(RuntimeError):
                requests.delete(load.baseline.API + "/data/fasnacht/test")
            with self.assertRaises(RuntimeError):
                requests.post(load.baseline.QUERY_URL, data={"update": "CLEAR ALL"})
        finally:
            requests.sessions.Session.request = original

    def test_multiple_listener_processes_are_all_sampled(self):
        with patch.object(load.subprocess, "check_output", side_effect=[
            "12\n11\n12\n", "20\n", "30\n", "40\n"]):
            pids = load.process_ids("http://localhost:8100")
        self.assertEqual(pids["api_11"], 11)
        self.assertEqual(pids["api_12"], 12)
        self.assertEqual(pids["existing_api"], 40)

    def test_target_port_does_not_allow_another_service(self):
        original = requests.sessions.Session.request
        try:
            load.baseline.install_transport_guard(load.baseline.Recorder(), api_url="http://localhost:8100")
            with self.assertRaises(RuntimeError):
                requests.get("http://localhost:8000/health")
        finally:
            requests.sessions.Session.request = original

    def test_experiment_rejects_writes_before_route_execution(self):
        from flask import Flask
        from types import SimpleNamespace
        from gunicorn_read_config import post_worker_init
        app = Flask(__name__)
        @app.post("/data/fasnacht/example")
        def mutation():
            raise AssertionError("Mutation must never execute")
        @app.get("/health")
        def health():
            return {"status": "ok"}
        post_worker_init(SimpleNamespace(wsgi=app))
        client = app.test_client()
        self.assertEqual(client.post("/data/fasnacht/example").status_code, 405)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Load-Worker", response.headers)

    def test_error_aborts_user(self):
        class Session:
            def request(self, *args, **kwargs):
                raise requests.Timeout()
        snapshot = {"api": {"cpu_seconds": 0, "rss_mib": 1}}
        with patch.object(load, "process_snapshot", return_value=snapshot):
            result = load.run_stage(1, 20, {"search_sorted": {"method": "POST", "path": "/data/search/fasnacht"}},
                                    [Session()], {"search_sorted": "x"}, {"api": 1})
        self.assertTrue(result["summary"]["aborted"])
        self.assertEqual(result["summary"]["errors"], 1)
        self.assertEqual(len(result["requests"]), 1)


if __name__ == "__main__":
    unittest.main()
