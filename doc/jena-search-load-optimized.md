# Concurrent readers after candidate-query optimization

## Workload

This follow-up uses the owned real-export Jena/API/Redis fixture and
`tools/migration/probe_search_load.py`. It changes test coverage only, not runtime
application code. Use its normal `--java`, `--jar`, fresh `--output`,
`--fasnacht-only`, `--fasnacht-export`, `--browser-preview`, `--fulltext-preview`
arguments. The wrapper stops its owned preview on success or failure.

Growth stages contain 1000/4000/12000 synthetic resources. At the final stage,
6000 are publicly readable and 9000 readable to the audit identity. Orphaned and
restricted grants are excluded; duplicate grants and tied titles are included.
The five mixed request shapes are count, sorted metadata page, date-filtered
count, structured date page and fulltext page. Result pages now contain 100 rows.
Dates have explicit readable grants, and their serialized years are independently
checked before concurrent reads.

Ten barrier-synchronized waves each at 1, 4 and 8 concurrent requests issue 130
requests, each using an independent HTTP session. Full responses must match
validated sequential references for that identity/request shape. The fixture
also traverses every visible metadata resource in 500-row pages, checks fulltext
totals and the last 100-row fulltext page, and checks current counts after removing
an asserted public role link. No write runs during the measured reader waves.

## Results

The owned `search-load-optimized-01` run passes **211 checks across
209 measured HTTP requests**. All 130 mixed-workload requests in the
reader waves return HTTP 200 and match their complete sequential reference.
The normal pre-growth fixture also passes 30 fulltext and 23 export/API checks.

| Concurrent requests | Samples | Median | Sample p95 | Maximum |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 10 | 1.25 s | 2.61 s | 2.61 s |
| 4 | 40 | 1.88 s | 3.96 s | 4.16 s |
| 8 | 80 | 2.99 s | 5.08 s | 5.33 s |

These medians mix five request shapes and two identities with equal representation
at each reader level. Sample p95 uses the nearest-rank statistic on this bounded
run. Even at eight simultaneous requests, the slowest measured response is
5.33 seconds; the existing 30-second HTTP timeout was not increased. Latency still
increases under load, so the result is not proof of linear throughput scaling.

All 6000 public / 9000 audit-visible metadata resources traverse in stable order,
without duplicate, missing or denied records. Fulltext totals and tail pages
also cover all authorized matches. Removing one public role assertion after the
reader waves reduces both identities' counts immediately despite retained grants.

The historical mixed-workload medians were 4.32 / 9.01 / 18.03 seconds. The new
1.25 / 1.88 / 2.99 seconds are encouraging despite the expanded workload, but
must not be presented as a controlled before/after speedup factor (see below).

[Aggregate samples and assertions](jena-search-load-optimized-results.json)
retain every measured request and the stage/count checks without credentials or
response contents. Source SHA-256 remains
`237fcf17a601db3ff25a784d9166bbfe6f94003069025ab0bd0f81978ead80d6`.
All owned services have stopped; shared services and production are unchanged.


## Interpretation and limits

The [earlier load rehearsal](jena-search-load.md) used 50-row pages, date nodes
without explicit grants and the former implicit text-index candidate window.
This run uses 100-row pages, explicitly readable dates and the corrected full
text candidate set. Historical timings therefore provide context, not a clean
A/B estimate of any one optimization. The preceding
[same-target query-order comparison](jena-search-candidates.md) isolates that
change separately.

The local 512 MiB Java heap and threaded development API are unchanged. This is
a bounded request workload, not eight complete browser sessions, a long-running
soak or production sizing. Production CPU/memory profiling, multi-process servers,
concurrent writes and broader identity/data distributions remain open. No new
cache, relaxed timeout or server-limit increase is introduced. Frontend grouped
pagination and the deferred GraphDB comparison remain separate steps.
