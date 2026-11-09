# Native Jena project transfer acceptance

The existing tools project dump/load functions now have an explicitly selected
Jena path. Implementation, command examples, scope and limits are documented in
[oldap-tools project transfer](../../oldap-tools/docs/jena-project-transfer.md).
The normal public API endpoints and public library signatures are unchanged.

The private Jena adapter uses native RDF 1.2 dataset serialization/parsing through
`JenaProjectTransfer.java`. Raw transfers recheck current root membership and
permission annotations on the server, restrict graph scope to registered project
parts and join the existing transaction owner. Export uses one snapshot; import
validates the whole payload and appends through the managed dataset so indexing
and rollback retain their normal transaction semantics.

The owned test `tools/migration/check_project_transfer.py` uses the real CLI,
a dedicated project, gzip files and a socket-only Redis for actual cache clearing.
No user Redis or existing development project is selected. One initial fixture
used a plain short-name literal; it was corrected to xsd:NCName before acceptance.

The retained results record **154 passing integration checks** (145 prior plus
9 transfer checks). Targeted offline regressions pass **14 library and
17 tools tests**. The test verifies cross-graph blank-node identity, language
literals, RDF 1.2 grants, four-graph round-trip, root refusal/revocation, joined
rollback, malformed/out-of-scope/default/reserved graph refusal and managed
fulltext commit/rollback behavior. All owned processes closed successfully.

This is an additive small-package migration path for provisioned projects,
not full backup recovery. Administrative users/roles, fulltext configuration,
binaries and policy are excluded; Jena dump requires --no-admin. The existing
262144-byte protocol request limit remains, and large/streaming datasets, legacy
GraphDB conversion, full administrative restore, ordinary export jobs and
production cache/concurrency/crash recovery remain separate gates.
