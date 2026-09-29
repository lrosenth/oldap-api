"""Offline checks for benchmark safety and non-overlapping timing accounting.

Run directly with ``python -m unittest discover -s tools -p test_read_performance.py``.
These tests never contact GraphDB or instantiate the application.
"""

import unittest
from unittest.mock import patch

import requests

from read_performance import QUERY_URL, Recorder, install_transport_guard


class RecorderTests(unittest.TestCase):
    def test_nested_timings_are_exclusive(self):
        recorder = Recorder()
        recorder.active = {"spans": {}}
        with patch(
            "read_performance.time.perf_counter", side_effect=[0, 0.002, 0.005, 0.010]
        ):
            with recorder.span("parent"):
                with recorder.span("child"):
                    pass
        self.assertAlmostEqual(recorder.active["spans"]["parent"]["inclusive_ms"], 10)
        self.assertAlmostEqual(recorder.active["spans"]["parent"]["exclusive_ms"], 7)
        self.assertAlmostEqual(recorder.active["spans"]["child"]["exclusive_ms"], 3)

    def test_wrapping_preserves_class_and_static_methods(self):
        class Example:
            @classmethod
            def class_method(cls):
                return cls.__name__

            @staticmethod
            def static_method(value):
                return value

        recorder = Recorder()
        recorder.wrap(Example, "class_method", "class")
        recorder.wrap(Example, "static_method", "static")
        self.assertEqual(Example.class_method(), "Example")
        self.assertEqual(Example().static_method(3), 3)


class ReadBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.transport = patch.object(requests.sessions.Session, "request")
        self.original = self.transport.start()
        self.original.return_value = requests.Response()
        install_transport_guard(Recorder())
        self.addCleanup(self.transport.stop)

    def test_mutations_and_remote_requests_never_reach_transport(self):
        cases = [
            ("POST", QUERY_URL + "/statements", {"data": {"update": "CLEAR ALL"}}),
            ("POST", QUERY_URL, {"data": {"update": "CLEAR ALL"}}),
            ("POST", QUERY_URL, {"data": {"query": "DELETE WHERE { ?s ?p ?o }"}}),
            ("GET", "https://example.org/", {}),
            ("DELETE", "http://localhost:8000/data/fasnacht/example", {}),
            ("POST", "http://localhost:8000/data/fasnacht/example", {}),
            (
                "POST",
                QUERY_URL,
                {
                    "data": {
                        "query": "SELECT * WHERE { SERVICE <http://example.org> { ?s ?p ?o } }"
                    }
                },
            ),
        ]
        for method, url, kwargs in cases:
            with self.subTest(method=method, url=url):
                with self.assertRaises(Exception):
                    requests.request(method, url, **kwargs)
        self.original.assert_not_called()

    def test_rdf_star_read_retains_original_acl_query(self):
        query = "SELECT * WHERE { <<?s <urn:role> ?r>> <urn:permission> ?p }"
        requests.post(QUERY_URL, data={"query": query})
        self.original.assert_called_once()
        self.assertEqual(self.original.call_args.kwargs["data"]["query"], query)
        self.assertEqual(self.original.call_args.kwargs["data"]["timeout"], "15")


if __name__ == "__main__":
    unittest.main()
