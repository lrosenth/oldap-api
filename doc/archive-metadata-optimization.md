# Archive metadata query optimization

Local follow-up to the integrated dating reader, on `experiment/dating-read-performance`. Public signatures, JSON shapes and RDF storage remain unchanged. API and library must be released together. No production or home deployment in this step.

## Operation-scoped vocabulary discovery

Search and its dating expansion use `JenaConnection._resource_schema_scope`. The first schema discovery per project queries live registrations; subsequent batches reuse only the resulting graph-name list. The scope is explicit, task-local, nestable and discarded on exit, including errors. Active transactions bypass reuse; non-read transport operations clear it before sending. Unscoped library callers continue to discover registrations on every query build. Concurrent external schema edits become visible on the next operation. Permissions, result rows and fulltext field configuration are not cached.

The existing search path already builds one resource factory for date expansion, and list-node namespaces are already prepared once per connection/project. No additional persistent model cache is introduced. Date search backend calls fall from 15 to 10; searches without date expansion still make three calls. This primarily saves repeated discovery round trips, not five expensive data queries.

## Broad metadata ACL join

The existing broad search subquery extracts resource and role from each RDF 1.2 permission annotation. Previously it joined user roles under another variable and then compared the two roles with a FILTER. The candidate binds the extracted role directly to the membership join variable. Permission numeric thresholds, explicit attached-role links, resource types and DISTINCT remain unchanged. Creator-only access is not added to search. Text and mandatory relationship-candidate paths retain their existing specialized plans.

A first candidate moved class-set resolution inside the ACL subquery. Owned run `metadata-queries-01` passed equivalence but showed no dependable additional speedup. That change was removed; the existing class-set planning remains in place.

## Reproducible comparison

`tools/migration/experiment_metadata_queries.py` uses the owned native preview runner and the captured nine overview payloads. It compares three variants sequentially:

- baseline: disable scoped reuse and restore the exact previous ACL join;
- scoped: retain schema reuse but restore the previous ACL join;
- candidate: integrated scoped reuse and direct role join.

Baseline restoration is confined to the test process, asserts recognition of the generated broad ACL block and counts rewrites; deployed runtime code has no global switches or monkeypatches. Complete responses and ordering are compared for public and audit readers, plus legacy/structured media dates, native permission/date/type fixtures, counts and 100-row pages at offsets 0 and 100. Per case/reader/variant: one warmup and four timed samples in alternating baseline/scoped/candidate/candidate/scoped/baseline order, repeated twice. Timed responses must also match.

Measurements are warm, local and sequential on an older representative export. Sums across nine separate searches are not browser page latency; they exclude parallelism and other requests. No direct production or live GraphDB measurement is claimed.

## Checks

103 focused Python tests passed across schema scope, transport, transactions, permissions, entailment, bulk reads and API serialization/detail paths. Compilation and whitespace checks passed. The earlier unrelated query-string test failures remain documented in the dating integration report.

## Final native results (2026-11-09)

Run `metadata-queries-02` passed all 31 recorded checks (24 real-data response comparisons, six paging/count comparisons and the native fixture group including direct search authorization). All 216 timed responses and 54 warmups also matched; 211 baseline/scoped queries were explicitly recognized and restored. Native fixture checks cover hidden/restricted/unassigned roles, missing asserted membership, creator-only resources, shared/missing dates, subproperties, multiple asserted types and calendar metadata.

| Warm local HTTP median | Previous integrated reader | Both optimizations | Reduction |
| --- | ---: | ---: | ---: |
| Public dating search | 432 ms | 367 ms | 15% |
| Audit dating search | 774 ms | 426 ms | 45% |
| Audit Agent metadata | 451 ms | 113 ms | 75% |
| Audit media preview metadata | 306 ms | 151 ms | 51% |
| Sum of nine public case medians | 1248 ms | 1123 ms | 10% |
| Sum of nine audit case medians | 3282 ms | 1286 ms | 61% |

The audit fixture has multiple roles and benefits most from eliminating the role cross-product. Schema reuse reliably removes five backend calls, but its isolated wall-time benefit varies with sample noise; do not infer a fixed percentage from the scope-only variant. Query placement alone did not earn its complexity and was rejected. Per-case/per-variant dispatch timing and call counts are preserved in [sanitized results](archive-metadata-optimization-results.json).

The sums are serial work across independent searches, **not measured archive page load times**. Results support joint API/library artifact acceptance and home.org verification; production remains unchanged. Factory/model construction already occurs once per date-expansion call, so no new model cache was needed.
