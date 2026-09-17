"""Administrative provisioning must not depend on private search visibility."""
from copy import deepcopy
import re

import pytest
from oldaplib.src.helpers.context import Context
from oldap_api import staging_area as staging

AREA = "urn:uuid:00000000-0000-0000-0000-000000000201"
ROLE = "https://example.org/archive/PrivateRole"
TOP = "urn:uuid:00000000-0000-0000-0000-000000000202"


def binding(value):
    return {"value": value}


class Connection:
    """Transactional topology double; actor intentionally has no private roles."""
    context_name = "PROVISION_TEST"
    userIri = "urn:uuid:00000000-0000-0000-0000-000000000203"

    def __init__(self, folders=None, admin=True, fail_at=None):
        Context(name=self.context_name)["museum"] = "https://example.org/archive/"
        self.folders = folders or {}
        self.admin = admin
        self.fail_at = fail_at
        self.updates = []
        self.active = False
        self.committed = False

    def query(self, query):
        raise AssertionError("Private search/out-of-transaction reads must not be used")

    def in_transaction(self):
        return self.active

    def transaction_start(self):
        self.active = True
        self.snapshot = deepcopy(self.folders)

    def transaction_abort(self):
        self.folders = self.snapshot
        self.active = False

    def transaction_commit(self):
        self.committed = True
        self.active = False

    def transaction_query(self, query):
        assert self.active
        if "staging-area-admin-delete" in query:
            return {"boolean": self.admin}
        if "staging-area-exists" in query:
            return {"boolean": True}
        assert "staging-system-state" in query
        rows = []
        for iri, (name, parent) in self.folders.items():
            row = {"defaultRole": binding(ROLE), "reservedFolder": binding(iri),
                   "reservedName": binding(name)}
            if parent:
                row["reservedParent"] = binding(parent)
            rows.append(row)
        return {"results": {"bindings": rows or [{"defaultRole": binding(ROLE)}]}}

    def transaction_update(self, query):
        assert self.active
        self.updates.append(query)
        if len(self.updates) == self.fail_at:
            raise RuntimeError("Injected write failure")
        iri = re.search(r'<([^>]+)> a shared:StagingFolder', query)[1]
        name = re.search(r'schema:name "([^"]+)"', query)[1]
        parent = re.search(r'shared:inStagingFolder <([^>]+)>', query)
        self.folders[iri] = (name, parent[1] if parent else None)
        assert f"oldap:attachedToRole <{ROLE}>" in query
        assert "oldap:createdBy" in query and "archive:record" in query
        assert f"oldap:hasDataPermission oldap:{'DATA_VIEW' if name == 'Mobile' else 'DATA_DELETE'}" in query


@pytest.fixture(autouse=True)
def coordination(monkeypatch):
    monkeypatch.setattr("oldaplib.src.resource_transaction.archive_coordination_enabled", lambda: False)
    monkeypatch.setattr(staging.RedisStagingMutationLock, "run", lambda self, op: op())


@pytest.mark.parametrize("existing", [{}, {TOP: ("top", None)}])
def test_admin_without_membership_completes_and_retries_idempotently(existing):
    con = Connection(deepcopy(existing))
    staging.provision_staging_system_folders(con, "museum", AREA)
    assert con.committed and len(con.folders) == 3
    if existing:
        assert con.folders[TOP] == ("top", None)
    expected = deepcopy(con.folders)
    count = len(con.updates)
    staging.provision_staging_system_folders(con, "museum", AREA)
    assert con.folders == expected and len(con.updates) == count


def test_unauthorized_cannot_discover_or_create_private_folders():
    con = Connection(admin=False)
    with pytest.raises(staging.StagingAreaPermissionDenied):
        staging.provision_staging_system_folders(con, "museum", AREA)
    assert not con.updates and not con.committed


def test_failure_rolls_back_all_missing_folders():
    con = Connection(fail_at=2)
    with pytest.raises(RuntimeError):
        staging.provision_staging_system_folders(con, "museum", AREA)
    assert con.folders == {} and not con.committed


def test_misplaced_existing_folder_is_not_repaired_or_duplicated():
    con = Connection({TOP: ("top", AREA)})
    with pytest.raises(staging.StagingStructureConflict):
        staging.provision_staging_system_folders(con, "museum", AREA)
    assert not con.updates


def test_http_command_dispatch_and_strict_payload(monkeypatch):
    from flask import Flask
    from oldap_api.views import instance_views
    app = Flask(__name__)
    app.register_blueprint(instance_views.instance_bp, url_prefix="/data")
    adapter = app.url_map.bind("localhost")
    endpoint, arguments = adapter.match("/data/museum/staging-system-folders", method="POST")
    assert endpoint.endswith("ensure_staging_system_folders")
    assert arguments == {"project": "museum"}
    calls = []
    monkeypatch.setattr(instance_views, "authenticated_connection", lambda: "connection")
    monkeypatch.setattr(instance_views, "provision_staging_system_folders", lambda *args: calls.append(args))
    with app.test_request_context(json={"stagingAreaIri": AREA}):
        response, status = instance_views.ensure_staging_system_folders.__wrapped__("museum")
        assert status == 200 and response.get_json() == {"ready": True}
    assert calls == [("connection", "museum", AREA)]
    with app.test_request_context(json={"stagingAreaIri": AREA, "attachedToRole": {"public": "DATA_DELETE"}}):
        _, status = instance_views.ensure_staging_system_folders.__wrapped__("museum")
        assert status == 400
    assert len(calls) == 1
