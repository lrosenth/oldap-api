# Bulk reads and remaining copy/export paths

## Implemented scope

`ResourceInstance.all_resources()` now chooses RDF 1.2 reifiers on a Jena
connection, retaining the existing GraphDB annotation syntax otherwise. Both
the asserted role link and its permission annotation must exist in the selected
project data graph. The authenticated user's role and the numeric DATA_VIEW
threshold remain authoritative. No creator or administrator bypass is added.
Public arguments, exact asserted-class matching and return shapes are unchanged:
IRIs and ordinary property values are lists, language-tagged properties become
LangString, and missing optional properties are empty lists. Counts are distinct
resource counts. Reads continue to join an existing resource transaction.
Query failures now retain their original error instead of being masked by an
undefined variable in the logging statement.

Existing pagination limits joined query rows. A multi-valued property can
therefore be incomplete at a page boundary. This limitation is now documented
in the method; changing pagination semantics is a separate compatibility task.

## Acceptance

`tools/migration/check_bulk_reads.py` follows the resource/fulltext acceptance
stages in the owned normal API runner. It checks projected values/missing values,
counts, single-valued pagination, permission thresholds, orphaned grants,
foreign-graph membership isolation, transaction-local reads and abort recovery.
Resources are created through the real API and listed by an ordinary user.
Only Redis object-cache I/O is suppressed; no connection/query implementation
is mocked. Offline tests also retain GraphDB dialect coverage, multi-valued
folding, transaction routing and original query errors.

The retained `jena-bulk-reads-results.json` records 91 passing integration
checks (85 earlier checks plus six bulk checks). The targeted offline suite
passed 21 tests. No live GraphDB regression was run.

## Remaining inventory

| Path | Finding / next work |
| --- | --- |
| Library `all_resources`; tools `staging_folders._load_staging_areas/_load_staging_folders` | Library query ported here; complete tools command and staging models still need acceptance. |
| API `/data/ofclass`, export `staging_snapshot` and `archive_snapshot` | Use the already ported `ResourceInstance.search`; complete export jobs are not yet accepted. |
| Tools ontology API import/dump and fulltext backup | Accepted in earlier normal API runner stages; distinct from raw project dump/restore. |
| Tools `graph_helpers.export_graphs_as_trig`, `load_project.import_trig/import_trig_gz` | GraphDB helpers retain RDF4J endpoints. Existing project dump/load now route explicitly to native scoped Jena transfer; small provisioned-project round-trip accepted, --no-admin required. Full admin/legacy restore and streaming remain open; see jena-project-transfer.md. |
| Library `archive_repository`, `archive_adoption`, `archive_inventory` | Inventory/adoption queries and folder snapshots migrated in `jena-archive-reads.md`; coordinated writes accepted in `jena-archive-writes.md`; complete inventory hydration remains a gate. |
| Library `archive_publication` | Publication/link service migrated in the next stage; see `jena-publication.md` for acceptance scope and remaining deployment gates. |
| Library media lookup by ID/IRI | Specialized legacy permission queries remain. |
| Library legacy `search_fulltext` | Native connector search remains separate from the accepted configured-field search. |
| Tools media-copy helpers | Binary upload/attachment workflow; no conclusion about end-to-end compatibility from query syntax alone. |

This inventory identifies concrete call paths, not a claim that every export or
copy workflow is migrated. No changes to tools callers or public signatures are
needed for the bulk-query dialect selection.
