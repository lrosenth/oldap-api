"""HTTP contract against isolated durable Redis; no application GraphDB writes."""

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from flask import Flask
from jsonschema import Draft202012Validator
import yaml
from oldaplib.test import test_mutation_gate as gate_fixture
from oldaplib.src.mutation_gate import (
    GATE_KEY,
    mutation_gate,
    mark_gate_uncertain,
    MutationGateUnavailable,
)
from oldaplib.src.writer_recovery import evidence_key, encoded
from oldaplib.src.xsd.iri import Iri
from oldap_api.views.writer_recovery_views import writer_recovery_bp

BASE = "/admin/writer-recovery"


class WriterRecoveryHttpTest(gate_fixture.MutationGateTest):
    def test_lost_durability_ack_is_unknown_and_same_id_recovers_it(self):
        with mutation_gate(client=self.client):
            mark_gate_uncertain()
        revision = self.request("get", "/status").json["revision"]
        body = {
            "operationId": self.id,
            "expectedRevision": revision,
            "reason": "Inspect interrupted operation",
        }
        with patch(
            "oldaplib.src.writer_recovery._durable",
            side_effect=MutationGateUnavailable("lost ack"),
        ):
            response = self.request("post", "/operations", json=body)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "RESULT_UNKNOWN")
        result = self.request("get", f"/operations/{self.id}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["state"], "awaiting_operator")

    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {
                "OLDAP_WRITER_DOMAIN": "fixture",
                "OLDAP_WRITER_RECOVERY_REDIS_URL": f"unix://{self.socket}?db=0",
                "OLDAP_WRITER_RECOVERY_ROLE_IRI": "urn:fixture:operator-role",
                "OLDAP_WRITER_RECOVERY_INVENTORY_SHA256": "d" * 64,
            },
        )
        self.env.start()
        self.actor = SimpleNamespace(
            userIri=Iri("urn:fixture:operator"),
            context_name="DEFAULT",
            query=Mock(return_value={"boolean": True}),
        )
        self.auth = patch(
            "oldap_api.authentication.Connection", return_value=self.actor
        )
        self.auth.start()
        app = Flask(__name__)
        app.register_blueprint(writer_recovery_bp)
        self.http = app.test_client()
        self.headers = {"Authorization": "Bearer fixture"}
        self.id = str(uuid4())
        self.schema = yaml.safe_load(
            (Path(__file__).parents[2] / "API-def/oldap-api.yaml").read_text()
        )

    def tearDown(self):
        self.auth.stop()
        self.env.stop()
        for key in self.client.scan_iter("oldap-api:staging:recovery:*"):
            self.client.delete(key)
        super().tearDown()

    def request(self, method, path, **kwargs):
        response = getattr(self.http, method)(
            BASE + path, headers=self.headers, **kwargs
        )
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        return response

    def validate(self, response, name):
        self.assertEqual(response.status_code, 200, response.json)
        Draft202012Validator(
            {
                "$ref": "#/components/schemas/" + name,
                "components": self.schema["components"],
            }
        ).validate(response.json)

    def begin(self):
        with mutation_gate(client=self.client):
            mark_gate_uncertain()
        status = self.request("get", "/status")
        self.validate(status, "WriterRecoveryStatus")
        self.assertNotIn("token", json.dumps(status.json))
        self.assertNotIn("transactions", json.dumps(status.json))
        body = {
            "operationId": self.id,
            "expectedRevision": status.json["revision"],
            "reason": "Investigate interrupted fixture operation",
        }
        result = self.request("post", "/operations", json=body)
        self.validate(result, "WriterRecoveryOperation")
        return body, result

    def test_http_exact_retry_evidence_states_release_and_redaction(self):
        body, first = self.begin()
        retry = self.request("post", "/operations", json=body)
        self.assertEqual(retry.json, first.json)
        self.assertEqual(first.json["state"], "awaiting_operator")
        refused = self.request("post", f"/operations/{self.id}/finish", json={})
        self.assertEqual(refused.status_code, 409)
        record = json.loads(
            self.client.get("oldap-api:staging:recovery:operation:" + self.id)
        )
        self.client.set(
            evidence_key(self.id),
            encoded(
                {
                    "version": 1,
                    "method": "docker-domain-restart-v1",
                    "domain": "fixture",
                    "inventoryDigest": "d" * 64,
                    "operationId": self.id,
                    "revision": body["expectedRevision"],
                    "runtime": {"privateHost": "never-exposed"},
                    "reconciliation": {"privateQuery": "never-exposed"},
                }
            ),
        )
        ready = self.request("get", f"/operations/{self.id}")
        self.assertEqual(ready.json["state"], "ready")
        self.assertTrue(ready.json["canFinish"])
        result = self.request("post", f"/operations/{self.id}/finish", json={})
        self.validate(result, "WriterRecoveryOperation")
        self.assertEqual(result.json["state"], "completed")
        for secret in (
            "never-exposed",
            record["owner"]["token"],
            "ownerRaw",
            "inventoryDigest",
            "transactions",
        ):
            self.assertNotIn(secret, json.dumps(result.json))
        with mutation_gate(client=self.client):
            successor = self.client.get(GATE_KEY)
            repeated = self.request("post", f"/operations/{self.id}/finish", json={})
            self.assertEqual(repeated.json, result.json)
            self.assertEqual(self.client.get(GATE_KEY), successor)

    def test_current_role_revocation_blocks_every_protected_route(self):
        self.begin()
        self.actor.query.return_value = {"boolean": False}
        self.assertEqual(
            self.request("get", "/capabilities").json,
            {"enabled": True, "canRecover": False},
        )
        for method, path, kwargs in [
            ("get", "/status", {}),
            ("get", f"/operations/{self.id}", {}),
            ("post", f"/operations/{self.id}/finish", {"json": {}}),
        ]:
            self.assertEqual(self.request(method, path, **kwargs).status_code, 403)
        self.assertIsNotNone(self.client.get(GATE_KEY))

    def test_disabled_capabilities_do_not_contact_database(self):
        with patch.dict(os.environ, {"OLDAP_WRITER_RECOVERY_ROLE_IRI": ""}):
            response = self.request("get", "/capabilities")
        self.validate(response, "WriterRecoveryCapabilities")
        self.assertEqual(response.json, {"enabled": False, "canRecover": False})
        self.actor.query.assert_not_called()

    def test_missing_auth_and_closed_inputs_are_rejected(self):
        self.assertEqual(self.http.get(BASE + "/status").status_code, 401)
        for value in (
            [],
            {"writer_terminated": True},
            {
                "operationId": self.id,
                "expectedRevision": "a" * 64,
                "reason": "long enough",
                "evidence": {},
            },
        ):
            self.assertEqual(
                self.request("post", "/operations", json=value).status_code, 400
            )
        self.assertEqual(
            self.request(
                "post", "/operations", data="x" * 9000, content_type="application/json"
            ).status_code,
            413,
        )
        self.assertEqual(
            self.request(
                "post", f"/operations/{self.id}/finish", json={"confirm": True}
            ).status_code,
            400,
        )
        self.assertEqual(self.request("get", "/operations/not-a-uuid").status_code, 400)
        self.assertIsNone(self.client.get(GATE_KEY))

    def test_transport_errors_are_sanitized_and_result_is_unknown(self):
        self.actor.query.side_effect = RuntimeError("redis://secret@private-host")
        response = self.request("get", "/status")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "RESULT_UNKNOWN")
        self.assertNotIn("secret", response.text)
