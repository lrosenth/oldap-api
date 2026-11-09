# Jena archive inventory and adoption queries

## Implementation

Archive inventory, adoption and folder revision snapshots now select RDF 1.2
permission annotations on Jena connections. GraphDB keeps the existing RDF-star
syntax. Three private query-building methods live on the existing
`ArchiveRepository` boundary and are reused by inventory and adoption:

- `_permission_pattern` reads grant values without projecting reifier identities.
  Access queries still require the asserted role link in the same project graph.
  State snapshots intentionally retain orphaned annotations as reviewed state.
- `_schema_dataset` combines only the project, shared and base ontology graphs
  as the default graph for hierarchy paths, and explicitly retains project data
  and administration as named graphs.
- `_class_pattern` accepts exact asserted types or ancestors in those schemas.
  Exact types also match when the schema graphs do not mention them. Foreign
  schema graphs cannot supply extra ancestry.

Adoption visibility uses direct joins for Jena. The old nested correlated
EXISTS/UNION form combined with hierarchy filters returned six identities in the
owned fixture, including a restricted medium and an orphaned grant; the direct
join returned the expected four. All callers already select or count DISTINCT
identities, so multiple qualifying roles do not create extra items/counts.
GraphDB keeps the established correlated-filter form. This is a reproduced query
shape difference, not a claim about the underlying Jena optimizer's root cause.

The existing creator exception, DATA_VIEW threshold, connected-subtree rules,
protected system branches, keyset cursor protocol, count deduplication, snapshot
hashing and stale-review rejection are preserved. Public signatures and response
shapes are unchanged. No query rewriting/parser layer or generalized graph
registry was added.

## Acceptance boundary

`tools/migration/check_archive_reads.py` uses an isolated normal Jena connection
and real shared-model folder loading. Its archive policy is explicitly supplied
by the fixture. Imported folder/media/target RDF exercises read semantics;
synthetic media rows are not evidence for complete media uploads or hydration.

Creating staging folders through the normal API correctly refused the first
fixture attempt because staging write coordination was unavailable. The fixture
therefore seeds owned RDF directly. No production coordination check was relaxed
or disabled. This stage tests queries and read-side stale-plan rejection. Subsequent coordinated
adoption-write acceptance is recorded in `jena-archive-writes.md`.

The checks cover mixed inventories and keyset continuation, creator/role access,
restricted and orphaned grants, schema isolation, cross-schema ancestry, exact
types absent from schemas, distinct counts, visible connected folder subtrees,
matching batch/single revisions, annotation-only snapshot changes, stale public
preflight, visible/hidden default targets, receipt hints with fresh authorization,
foreign-graph revision isolation, transaction-local revisions and stale inventory
cursors. Query results and domain checks are not mocked. The shared runner still
suppresses only Redis object-cache I/O and closes its owned services afterward.

Offline tests verify dialect selection and active-transaction routing, plus the
existing archive domain, cursor, plan and aggregation regressions. The existing
RDFLib aggregation fixture now supplies an explicit GraphDB-mode connection;
its data/expected results are unchanged.

## Remaining work

Coordinated adoption writes and structural audit/receipts were subsequently
accepted in `jena-archive-writes.md`. Complete inventory hydration/HTTP workflows, raw project transfer,
specialized media queries and export jobs remain separate acceptance gates.
GraphDB syntax is covered offline; no shared GraphDB service is tested here.

## Results

The retained `jena-archive-reads-results.json` contains 115 passing owned checks
(102 earlier plus 13 archive-read checks). Targeted library regressions pass
62 tests plus 21 subtests; API archive-route regressions pass 11 tests plus
13 subtests. RDFLib reports existing deprecation warnings in the offline
aggregation fixture. No shared service was touched.
