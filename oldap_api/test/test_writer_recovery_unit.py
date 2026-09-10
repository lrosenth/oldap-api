"""Fresh operational authorization, revocation and actor binding without live RDF."""

import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.helpers.oldaperror import (
    OldapErrorNoPermission,
    OldapErrorConfiguration,
)
from oldap_api.writer_recovery import WriterRecoveryService, require_recovery_role


class WriterRecoveryServiceTest(unittest.TestCase):
    def test_role_query_has_explicit_network_timeout(self):
        from oldaplib.src.connection import Connection

        connection = object.__new__(Connection)
        connection._userdata = object()
        connection._query_url = "http://fixture.invalid/repositories/test"
        connection._dbuser = None
        connection._dbpassword = None
        with patch("oldaplib.src.connection.requests.post") as post:
            post.return_value.ok = True
            post.return_value.status_code = 200
            post.return_value.json.return_value = {"boolean": True}
            self.assertEqual(
                connection.query("ASK {}", timeout=(5, 10)), {"boolean": True}
            )
            self.assertEqual(post.call_args.kwargs["timeout"], (5, 10))
            connection.query("ASK {}")
            self.assertNotIn("timeout", post.call_args.kwargs)

    def setUp(self):
        self.connection = SimpleNamespace(
            userIri=Iri("urn:test:operator"),
            context_name="DEFAULT",
            query=Mock(return_value={"boolean": True}),
        )
        self.recovery = Mock()
        with patch.dict(
            os.environ,
            {
                "OLDAP_WRITER_RECOVERY_ROLE_IRI": "urn:oldap:roles:WriterRecoveryOperator"
            },
        ):
            self.service = WriterRecoveryService(
                self.connection, recovery=self.recovery
            )

    def test_every_call_rechecks_current_active_role_in_rdf(self):
        self.service.status()
        self.service.operation("operation")
        self.service.begin(
            operation_id="operation",
            expected_revision="revision",
            reason="Investigate failed write",
        )
        self.service.finish(operation_id="operation")
        self.assertEqual(self.connection.query.call_count, 4)
        query = self.connection.query.call_args.args[0]
        self.assertIn("oldap:isActive true", query)
        self.assertIn("oldap:hasRole <urn:oldap:roles:WriterRecoveryOperator>", query)
        self.assertIn("a oldap:Role", query)
        self.recovery.finish.assert_called_once_with(
            operation_id="operation", actor="urn:test:operator"
        )

    def test_revocation_denies_release_and_read_even_with_cached_admin_rights(self):
        self.service.status()
        self.connection.userdata = SimpleNamespace(
            inProject={"oldap:SystemProject": ["ADMIN_OLDAP"]}
        )
        self.connection.query.return_value = {"boolean": False}
        for call in (
            lambda: self.service.finish(operation_id="operation"),
            self.service.status,
            lambda: self.service.operation("operation"),
        ):
            with self.assertRaises(OldapErrorNoPermission):
                call()
        self.recovery.finish.assert_not_called()
        self.recovery.operation.assert_not_called()

    def test_unavailable_permission_query_never_releases(self):
        self.connection.query.side_effect = RuntimeError("database unavailable")
        with self.assertRaises(RuntimeError):
            self.service.finish(operation_id="operation")
        self.recovery.finish.assert_not_called()

    def test_missing_or_unsafe_role_configuration_is_denied(self):
        for role in ("", "oldap:Role", "urn:role> ?s ?p ?o", "https://role\n"):
            with self.subTest(role=role), self.assertRaises(OldapErrorConfiguration):
                require_recovery_role(self.connection, role)
        self.connection.query.assert_not_called()
