# Relationship search: candidate selection before access joins

## Decision and implementation (2026-10-31)

`ResourceInstance.search` now adds a distinct resource candidate subquery after class-set selection and before
permission joins for Jena searches containing a mandatory root-property
EQ comparison with an IRI or QName. It chooses the first eligible comparison in
an expression containing no OR. Other comparisons remain unchanged. GraphDB
queries and public API/library signatures are unchanged.

The readable sequence is: resolve the small set of eligible classes, find
relationship candidates, check access and all search conditions, then sort and
page the permitted resources. Class-set selection must precede all resource
bindings so ARQ does not repeat that independent scan for every candidate. The candidate
subquery projects only `?res`; it reuses the normal property matcher, including
scoped subproperties, existing inverse rules and protected predicates. It does
not grant access. All original ACLs and filters remain authoritative. Keeping the
original comparison also preserves the existing multivalue/filter behavior.

OR expressions (including grouped OR), linked-resource comparisons, absence and
literal comparisons do not themselves supply candidates. A required root IRI
comparison can still narrow an AND containing those other conditions. There is
no result cache, new index, stored reverse relationship or general OWL reasoner.

## Evidence before implementation

One real Fasnacht parent with two children, three sequential samples per case:

| HTTP request shape | Original median | Direct-only diagnostic | Early object binding diagnostic |
| --- | ---: | ---: | ---: |
| Project-wide reverse lookup | 7355 ms | 6998 ms | 6948 ms |
| Class, names and sorting (frontend shape) | 3054 ms | 2669 ms | 2641 ms |

The metadata queries consumed approximately 9 ms; the main search dominated.
Removing relationship expansion was therefore not the primary improvement.
The direct-only control changes general semantics and is not a runtime option.

On a disposable copy of the same closed TDB2 dataset, native query execution
without HTTP measured 6393 → 352 ms for the project-wide query and 2596 → 757 ms
for the frontend-shaped query when candidate selection preceded access joins.
All baseline/candidate result hashes matched. These native timings must not be
compared directly with end-to-end HTTP timings.

Aggregate diagnostic evidence: `jena-parts-performance-results.json`.
Private query texts and source data remain outside Git.

## Acceptance and reproduction

The library's `tools/migration/probe_model_reads.py` runs native Fuseki checks,
including relationship candidates with only a subproperty assertion, duplicate
paths, denied resources, AND/OR/grouping, absence, foreign graph exclusion,
sorting, paging, counts, immediate membership revocation and rollback.

The API's `tools/migration/probe_api_jena.py --fasnacht-only --fasnacht-export
<private-native-export> --profile-parts --java <java> --jar <fuseki-jar> --output
<new-private-directory>` rebuilds a disposable target, repeats complete model
and real-export checks, and measures three HTTP samples per diagnostic variant.
`current` denotes the actual current runtime; historical `baseline` entries in
the earlier evidence denote the unoptimized implementation. Diagnostic patches
exist only inside this runner, never in the application configuration.

Object-cache I/O is disabled. Timings use warm sequential local runs, not a load
benchmark. Production datasets, real-user provisioning, browser/cache behavior
and concurrency remain separate acceptance work. The optimization makes no
claim about arbitrary filter selectivity; the first eligible relation is used
without adding a statistics engine or complicating the public filter format.

## Installed implementation: HTTP acceptance

The full fresh-target Fasnacht import and real-export checks pass, including all
five parent comparisons against independently computed readable children.
With the actual runtime candidate subquery, median HTTP time is **524 ms** for
the project-wide query (previously 7355 ms), and **924 ms** for the frontend-shaped
query (previously 3054 ms). These are separate sequential runs on the same source
and model, not an interleaved benchmark. Each timing uses three samples.

All 166 library integration checks, 27 focused offline tests and 24 focused API
checks pass. The ten new library checks include a resource linked only through a
subproperty and immediate revocation within a transaction. Source/live systems
were not modified. Evidence: `jena-relationship-candidates-results.json` and
`../../oldaplib/docs/migration/jena-relationship-candidates-results.json`.

## Growth acceptance and class-selection correction (2026-10-31)

The next fixture creates 1,000 children: 500 readable, 250 with orphaned grant
annotations, and 250 with permissions below VIEW. Half the links use a
subproperty. Duplicate property paths and repeated names exercise deduplication
and the stable IRI sort tie-break. Ten pages of 50 traverse every readable child.

This exposed a query-order regression: placing relationship candidates before
the independent class-set query made a class-filtered count exceed the fixture's
10-second request timeout, while the class-free count took 347 ms. The class-set
query now runs first, then relationship candidates, then the original access and
filter checks. No new query abstraction, cache or public parameter was needed.

Corrected synthetic results (library transport, **not API HTTP**):

| Operation | Median |
| --- | ---: |
| Count with class filter (3 samples) | 339 ms |
| First sorted page, 50 resources (3 samples) | 452 ms |
| Full traversal, per page (10 pages) | 477 ms |
| Broad relationship first in a two-condition AND (3 samples) | 431 ms |
| Selective relationship first in the same AND (3 samples) | 342 ms |

Both AND orders return exactly the same ten resources. The remaining difference
does not justify automatic selectivity estimation in this step. Complete page
contents, reverse sorting, beyond-end paging, counts, permission revocation and
rollback pass. All 185 native checks (19 added growth assertions) and 27 focused
offline tests pass. This is bounded synthetic growth acceptance, not a production
concurrency or HTTP latency guarantee.

Reproduce with the library model-read runner's `--relationship-growth` flag and
the usual `--java`, `--jar`, and new `--output` directory. The optional fixture
uses a 120-second transaction lease for its many requests; the per-request
10-second timeout is unchanged. Updates are chunked below the transport limit.
Evidence: `../../oldaplib/docs/migration/jena-relationship-growth-results.json`.

The repeated real-Fasnacht HTTP rehearsal also passes all 24 checks after this
correction. Current medians are 452 ms for the project-wide reverse lookup and
946 ms for the class/name/sorted frontend shape (previous stage: 524/924 ms).
The small sorted-query difference is not a demonstrated regression in these
separate local runs; the original pre-optimization baseline was 7355/3054 ms.
All five real parent comparisons still match. Evidence:
`jena-relationship-growth-api-results.json`.
