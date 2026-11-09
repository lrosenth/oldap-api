# Fulltext query placement

## Decision

Evaluate Jena text matches before root permission/property/list checks, after the
independent class set and any mandatory relationship candidates. This lets text
matches bind the root instead of invoking the text property function for the
resources produced by earlier joins. Referenced-source permission checks remain
inside the text pattern. Root grants still require asserted role membership and
an RDF 1.2 grant; every filter precedes scoring, sorting and paging. There is no
index hit limit, permission cache, public signature change or GraphDB reorder.

The change is local to `ResourceInstance.search.append_resource_match`, shared
by count and result queries. It only moves the existing Jena pattern. A grouped
candidate subquery was also measured; its small additional gain did not justify
another aggregation layer in the runtime query.

## Same-target comparison

The owned `fasnacht-fulltext-perf-01` rehearsal activates the real Fasnacht export
through the normal YAML/API path and then measures three plans. Six HTTP request
shapes are repeated three times per plan. Full JSON responses, including scores,
returned values and order, must equal the original plan exactly. No model/data
or index change occurs between the measured variants. These are sequential local
measurements, not production capacity or concurrent-load guarantees.

| HTTP request | Original median ms | Early text median ms | Grouped median ms |
| --- | ---: | ---: | ---: |
| Title | 3302.61 | 59.12 | 53.67 |
| Title count | 3236.88 | 56.17 | 51.37 |
| Media: two words | 1671.38 | 86.73 | 80.99 |
| Media: linked title, two words | 1745.86 | 143.42 | 128.52 |
| Extracted PDF text | 3274.17 | 58.78 | 55.30 |
| Media: direct OR linked title | 1845.07 | 135.66 | 133.47 |

[Measurement samples](jena-fulltext-performance-results.json) retain all 54
request durations. Native generated queries remain in the private probe output.

## Reproduction

Use `tools/migration/profile_fasnacht_fulltext.py` with the normal
`probe_api_jena.py` arguments: `--java`, `--jar`, a fresh `--output`,
`--fasnacht-only`, `--fasnacht-export`, `--browser-preview` and
`--fulltext-preview`. It wraps only the disposable process and compares late,
early and grouped placement even after the runtime builder is optimized. Fixed
profile cases intentionally have no ordinary property/list filters; the native
regression suite covers their combination with text search. The wrapper locates
existing root-grant clauses and fails if those markers change. Stop the owned
preview using its `browser-stop` file.

## Validation

The final normal-adapter run `fasnacht-fulltext-perf-02` passes 26 fulltext and
23 real-export checks, including current permission revocation and concurrent
searches. Its 22 timed searches have median 76 ms and maximum 493 ms. The native
model/search suite passes 169 checks, including fulltext with property/list filters,
subclasses, paging, multivalue projections, commit/rollback/deletion and role
removal. All 27 offline fulltext configuration tests pass. Python syntax and
whitespace checks pass. The unchanged browser returns the same 20 matches
(14 media, five objects, one event); screenshot evidence stays in the private
run directory. Both word orders return those counts. The source export SHA-256
remains unchanged and owned services are stopped after acceptance. Image/PDF binary services are outside this performance rehearsal.
An older native negative test still rejected ordinary two-word input. It has
been replaced with positive order-independent and multivalue AND checks plus
negative missing-word and cross-value phrase cases, matching the user's selected
search semantics.

## Remaining work

Production load, analyzer/language behavior and the deferred GraphDB comparison
remain separate gates. Browser elapsed time also includes other archive metadata
requests and rendering; the table measures search HTTP calls, not page readiness.
