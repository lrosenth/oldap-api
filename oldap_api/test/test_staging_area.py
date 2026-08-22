"""Focused policy and transaction tests for Step 11B Staging protection."""

from __future__ import annotations

from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.xsd.iri import Iri
import pytest

from oldap_api.staging_area import (
    GraphDbStagingAreaRepository,
    StagingAreaPermissionDenied,
    StagingAreaServiceUnavailable,
    StagingAreaValidationError,
    StagingGraph,
    StagingStructureConflict,
    StagingSystemFolderPolicy,
    run_staging_mutation,
)
from oldap_api.staging_lock import (
    RedisStagingMutationLock,
    StagingMutationLockUnavailable,
)
from oldap_api.mobile_media.commit_lock import RedisMobileMediaCommitLock

AREA = "urn:uuid:00000000-0000-0000-0000-000000000201"
TOP = "urn:uuid:00000000-0000-0000-0000-000000000202"
MOBILE = "urn:uuid:00000000-0000-0000-0000-000000000203"
TRASH = "urn:uuid:00000000-0000-0000-0000-000000000204"
USER_FOLDER = "urn:uuid:00000000-0000-0000-0000-000000000205"
DEFAULT_ROLE = "http://oldap.org/fasnacht#DefaultRole"
ACTOR = "urn:uuid:00000000-0000-0000-0000-000000000206"


def binding(value: str) -> dict[str, str]:
    return {"type": "uri", "value": value}


def literal(value: str) -> dict[str, str]:
    return {"type": "literal", "value": value}


def result(rows: list[dict]) -> dict:
    return {"results": {"bindings": rows}}


def configure_context(name: str) -> None:
    Context(name=name)["fasnacht"] = "http://oldap.org/fasnacht#"


def test_resolves_project_graph_for_a_fresh_bearer_context() -> None:
    class FreshBearerConnection:
        context_name = "STAGING_FRESH_BEARER_CONTEXT"

        def query(self, query: str):
            assert "# staging-project-namespace" in query
            assert '"fasnacht"^^<http://www.w3.org/2001/XMLSchema#NCName>' in query
            return result([{"namespace": binding("http://oldap.org/fasnacht#")}])

    graph = StagingGraph.resolve(FreshBearerConnection(), "fasnacht")

    assert graph.project_namespace == "http://oldap.org/fasnacht#"
    assert graph.data_graph_iri == "http://oldap.org/fasnacht#data"


class PolicyConnection:
    """Return deterministic GraphDB facts for generic-operation guards."""

    context_name = "STAGING_POLICY_TEST"

    def __init__(
        self,
        *,
        top: set[str] | None = None,
        mobile: set[str] | None = None,
        trash: set[str] | None = None,
        protected: set[str] | None = None,
        reserved: list[tuple[str, str, str | None]] | None = None,
    ) -> None:
        configure_context(self.context_name)
        self.top = top or set()
        self.mobile = mobile or set()
        self.trash = trash or set()
        self.protected = protected or set()
        top_parent = next(iter(self.top), None)
        self.reserved = [
            *((iri, "top", None) for iri in self.top),
            *((iri, "Mobile", top_parent) for iri in self.mobile),
            *((iri, "Trash", top_parent) for iri in self.trash),
            *(reserved or []),
        ]

    def query(self, query: str):
        if "# staging-system-state" in query:
            rows = [
                {
                    "defaultRole": binding(DEFAULT_ROLE),
                    "reservedFolder": binding(iri),
                    "reservedName": literal(name),
                    **({"reservedParent": binding(parent)} if parent else {}),
                }
                for iri, name, parent in self.reserved
            ] or [{"defaultRole": binding(DEFAULT_ROLE)}]
            return result(rows)
        if "# protected-staging-folder" in query:
            return {"boolean": any(f"<{iri}>" in query for iri in self.protected)}
        if "# protected-mobile-folder" in query:
            return {"boolean": any(f"<{iri}>" in query for iri in self.mobile)}
        raise AssertionError(f"Unexpected query: {query}")


def folder_payload(
    name: str,
    *,
    parent: str | None = None,
    permission: str = "DATA_DELETE",
) -> dict:
    payload = {
        "schema:name": [name],
        "shared:inStagingArea": [AREA],
        "attachedToRole": {DEFAULT_ROLE: permission},
    }
    if parent is not None:
        payload["shared:inStagingFolder"] = [parent]
    return payload


def test_allows_only_valid_first_system_folder_provisioning() -> None:
    policy = StagingSystemFolderPolicy(PolicyConnection(), "fasnacht")
    policy.assert_create_allowed("shared:StagingFolder", folder_payload("top"))

    policy = StagingSystemFolderPolicy(PolicyConnection(top={TOP}), "fasnacht")
    policy.assert_create_allowed(
        "shared:StagingFolder",
        folder_payload("Mobile", parent=TOP, permission="DATA_VIEW"),
    )
    policy.assert_create_allowed(
        "shared:StagingFolder", folder_payload("Trash", parent=TOP)
    )


@pytest.mark.parametrize(
    "connection,payload,message",
    [
        (
            PolicyConnection(top={TOP}),
            folder_payload("top"),
            "already has a root top",
        ),
        (
            PolicyConnection(top={TOP}, mobile={MOBILE}),
            folder_payload("Mobile", parent=TOP, permission="DATA_VIEW"),
            'already has a "Mobile"',
        ),
        (
            PolicyConnection(top={TOP}),
            folder_payload("Mobile", parent=USER_FOLDER, permission="DATA_VIEW"),
            "must be a direct child",
        ),
        (
            PolicyConnection(top={TOP}),
            folder_payload("Mobile", parent=TOP, permission="DATA_DELETE"),
            "must grant only DATA_VIEW",
        ),
        (
            PolicyConnection(top={TOP}, mobile={MOBILE}),
            folder_payload("Photos", parent=MOBILE),
            "cannot contain child folders",
        ),
        (
            PolicyConnection(top={TOP}),
            folder_payload("MOBILE", parent=TOP, permission="DATA_VIEW"),
            "exact spelling",
        ),
    ],
)
def test_rejects_duplicate_misplaced_or_unprotected_system_folder_creation(
    connection: PolicyConnection, payload: dict, message: str
) -> None:
    with pytest.raises(StagingStructureConflict, match=message):
        StagingSystemFolderPolicy(connection, "fasnacht").assert_create_allowed(
            "shared:StagingFolder", payload
        )


@pytest.mark.parametrize(
    "connection,message",
    [
        (
            PolicyConnection(reserved=[(USER_FOLDER, "MOBILE", TOP)]),
            "invalid spelling",
        ),
        (
            PolicyConnection(reserved=[(MOBILE, "Mobile", USER_FOLDER)]),
            "direct child of top",
        ),
        (
            PolicyConnection(top={TOP, USER_FOLDER}),
            "duplicate reserved",
        ),
    ],
)
def test_existing_ambiguous_reserved_folders_block_further_provisioning(
    connection: PolicyConnection, message: str
) -> None:
    with pytest.raises(StagingStructureConflict, match=message):
        StagingSystemFolderPolicy(connection, "fasnacht").assert_create_allowed(
            "shared:StagingFolder",
            folder_payload("Mobile", parent=TOP, permission="DATA_VIEW"),
        )


def test_blocks_every_generic_protected_folder_mutation() -> None:
    connection = PolicyConnection(protected={TOP, MOBILE, TRASH}, mobile={MOBILE})
    policy = StagingSystemFolderPolicy(connection, "fasnacht")

    for operation in (
        lambda: policy.assert_update_allowed(TOP, {"schema:name": ["renamed"]}),
        lambda: policy.assert_update_allowed(
            MOBILE, {"oldap:attachedToRole": {DEFAULT_ROLE: "DATA_DELETE"}}
        ),
        lambda: policy.assert_move_allowed(MOBILE, TOP),
        lambda: policy.assert_move_allowed(USER_FOLDER, MOBILE),
        lambda: policy.assert_delete_allowed(TOP),
        lambda: policy.assert_delete_allowed(MOBILE),
        lambda: policy.assert_update_allowed(TRASH, {"schema:name": ["Bin"]}),
        lambda: policy.assert_move_allowed(TRASH, TOP),
        lambda: policy.assert_delete_allowed(TRASH),
        lambda: policy.assert_transform_allowed(TRASH),
        lambda: policy.assert_transform_allowed(MOBILE),
        lambda: policy.assert_transform_target_allowed("shared:StagingFolder"),
        lambda: policy.assert_staging_area_delete_allowed("fasnacht:StagingArea"),
        lambda: policy.assert_staging_area_transform_allowed("fasnacht:StagingArea"),
        lambda: policy.assert_transform_target_allowed("fasnacht:StagingArea"),
    ):
        with pytest.raises(StagingStructureConflict):
            operation()

    with pytest.raises(StagingStructureConflict):
        policy.assert_update_allowed(MOBILE, {"schema:comment": ["Visible note"]})
    policy.assert_delete_allowed(USER_FOLDER)
    policy.assert_staging_area_delete_allowed("fasnacht:Place")
    policy.assert_staging_area_transform_allowed("fasnacht:Place")
    policy.assert_transform_target_allowed("fasnacht:Place")


def test_blocks_generic_rename_to_any_reserved_system_folder_name() -> None:
    policy = StagingSystemFolderPolicy(PolicyConnection(), "fasnacht")

    for reserved_name in ("top", "Mobile", "Trash", "mobile"):
        with pytest.raises(StagingStructureConflict, match="Reserved"):
            policy.assert_update_allowed(USER_FOLDER, {"schema:name": [reserved_name]})


def test_staging_and_mobile_commits_share_one_cross_worker_lease() -> None:
    assert RedisStagingMutationLock.LOCK_NAME == RedisMobileMediaCommitLock.LOCK_NAME


def test_staging_lock_uses_a_cross_thread_renewable_bounded_lease() -> None:
    class FakeLease:
        released = 0

        def acquire(self, *, blocking):
            assert blocking is True
            return True

        def extend(self, additional_time, *, replace_ttl):
            raise AssertionError("A completed short operation needs no renewal.")

        def release(self):
            self.released += 1

    class FakeRedis:
        def __init__(self):
            self.lease = FakeLease()
            self.arguments = None

        def lock(self, name, *, timeout, blocking_timeout, thread_local):
            self.arguments = (name, timeout, blocking_timeout, thread_local)
            return self.lease

    client = FakeRedis()
    guard = RedisStagingMutationLock(client)

    assert guard.run(lambda: "written") == "written"
    assert client.arguments == (
        guard.LOCK_NAME,
        guard.LEASE_SECONDS,
        guard.WAIT_SECONDS,
        False,
    )
    assert client.lease.released == 1

    with pytest.raises(KeyboardInterrupt):
        guard.run(lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert client.lease.released == 2


def test_staging_mutation_maps_coordination_failure_to_retryable_http_error(
    monkeypatch,
) -> None:
    class UnavailableLock:
        def run(self, operation):
            raise StagingMutationLockUnavailable("Redis is unavailable.")

    monkeypatch.setattr(
        "oldap_api.staging_area.RedisStagingMutationLock", UnavailableLock
    )

    with pytest.raises(StagingAreaServiceUnavailable, match="Redis is unavailable"):
        run_staging_mutation("shared:StagingFolder", lambda: None)


class TransactionConnection:
    """Scriptable transaction fake for atomic StagingArea teardown."""

    context_name = "STAGING_DELETE_TEST"
    userIri = Iri(ACTOR)

    def __init__(
        self,
        *,
        folders: list[dict] | None = None,
        admin: bool = True,
        permitted_resources: tuple[str, ...] = (),
        has_contents: bool = False,
        has_references: bool = False,
        remaining: bool = False,
        fail_update: bool = False,
    ) -> None:
        configure_context(self.context_name)
        self.folders = folders if folders is not None else system_folder_rows()
        self.admin = admin
        self.permitted_resources = permitted_resources
        self.has_contents = has_contents
        self.has_references = has_references
        self.remaining = remaining
        self.fail_update = fail_update
        self.started = 0
        self.committed = 0
        self.aborted = 0
        self.updates: list[str] = []
        self.queries: list[str] = []

    def query(self, query: str):
        raise AssertionError("Deletion must use transaction_query.")

    def transaction_start(self) -> None:
        self.started += 1

    def transaction_query(self, query: str):
        self.queries.append(query)
        if "# staging-area-deletion-target" in query:
            return result(self.folders)
        if "# staging-area-exists" in query:
            return {"boolean": True}
        if "# staging-area-admin-delete" in query:
            return {"boolean": self.admin}
        if "# staging-area-resource-delete-permissions" in query:
            return result(
                [
                    {"resource": binding(resource)}
                    for resource in self.permitted_resources
                ]
            )
        if "# staging-area-contents" in query:
            return {"boolean": self.has_contents}
        if "# staging-area-external-references" in query:
            return {"boolean": self.has_references}
        if "# remaining-staging-area-targets" in query:
            return {"boolean": self.remaining}
        raise AssertionError(f"Unexpected query: {query}")

    def transaction_update(self, query: str) -> None:
        self.updates.append(query)
        if self.fail_update:
            raise OldapError("forced update failure")

    def transaction_commit(self) -> None:
        self.committed += 1

    def transaction_abort(self) -> None:
        self.aborted += 1


def system_folder_rows() -> list[dict]:
    return [
        {"folder": binding(TOP), "name": literal("top")},
        {
            "folder": binding(MOBILE),
            "name": literal("Mobile"),
            "parent": binding(TOP),
        },
        {
            "folder": binding(TRASH),
            "name": literal("Trash"),
            "parent": binding(TOP),
        },
    ]


def test_atomically_deletes_only_the_exact_empty_system_structure() -> None:
    connection = TransactionConnection()
    target = GraphDbStagingAreaRepository(connection, "fasnacht").delete_empty(AREA)

    assert target.resources == (AREA, TOP, MOBILE, TRASH)
    assert connection.started == 1
    assert connection.committed == 1
    assert connection.aborted == 0
    assert len(connection.updates) == 1
    for resource in target.resources:
        assert f"<{resource}>" in connection.updates[0]
    assert "oldap:attachedToRole" in connection.updates[0]
    admin_query = next(
        query for query in connection.queries if "# staging-area-admin-delete" in query
    )
    assert "oldap:inProject oldap:SystemProject" in admin_query
    assert "?anyProject" not in admin_query


def test_rejects_invalid_staging_area_iri_as_client_input() -> None:
    connection = TransactionConnection()

    with pytest.raises(StagingAreaValidationError) as raised:
        GraphDbStagingAreaRepository(connection, "fasnacht").delete_empty("not an IRI")

    assert raised.value.status == 400
    assert connection.started == 0


@pytest.mark.parametrize(
    "connection,error",
    [
        (TransactionConnection(has_contents=True), StagingStructureConflict),
        (TransactionConnection(has_references=True), StagingStructureConflict),
        (
            TransactionConnection(admin=False, permitted_resources=(AREA, TOP, MOBILE)),
            StagingAreaPermissionDenied,
        ),
        (
            TransactionConnection(
                folders=system_folder_rows()
                + [
                    {
                        "folder": binding(USER_FOLDER),
                        "name": literal("Photos"),
                        "parent": binding(TOP),
                    }
                ]
            ),
            StagingStructureConflict,
        ),
        (
            TransactionConnection(
                folders=system_folder_rows()
                + [
                    {
                        "folder": binding(USER_FOLDER),
                        "name": literal("Mobile"),
                        "parent": binding(TOP),
                    }
                ]
            ),
            StagingStructureConflict,
        ),
    ],
)
def test_rejects_nonempty_unauthorized_or_ambiguous_teardown(
    connection: TransactionConnection, error: type[Exception]
) -> None:
    with pytest.raises(error):
        GraphDbStagingAreaRepository(connection, "fasnacht").delete_empty(AREA)
    assert connection.committed == 0
    assert connection.aborted == 1
    assert connection.updates == []


def test_forced_graphdb_failure_rolls_back_the_complete_delete() -> None:
    connection = TransactionConnection(fail_update=True)

    with pytest.raises(OldapError, match="forced update failure"):
        GraphDbStagingAreaRepository(connection, "fasnacht").delete_empty(AREA)

    assert connection.committed == 0
    assert connection.aborted == 1
    assert len(connection.updates) == 1
