# Search growth and concurrent-reader rehearsal

Follow-up: [optimized 100-row concurrent-reader run](jena-search-load-optimized.md)
uses readable dates and complete text candidates. The measurements below retain
the earlier workload; the current harness uses the follow-up settings.

## Scope

`tools/migration/probe_search_load.py` extends the disposable real-export API
fixture. It leaves source files and shared services unchanged. The fixture runs
Jena with a 512 MiB Java heap, the local threaded Flask server and owned Redis.
It is a bounded diagnostic workload, not a production capacity guarantee.

Three cumulative synthetic sizes (1000, 4000, 12000 resources) exercise public
and audit identities. Every eight resources include four public, two internal,
one orphan public grant and one grant below VIEW. Public objects also remain
visible to audit. Selected resources have duplicate grants; titles contain ties.
One hundred shared date nodes cover 1900–1999, and all names include a fixture
fulltext marker. Expected IDs, order and date membership are computed in Python
independently of query results. No source accounts/passwords are restored.

Checks cover counts, sorted metadata pages, 1900–1949 overlap counts, structured
date pages, fulltext pages, complete paged traversal, a 5000-row result window,
and current permission removal after readers complete. API paging beyond 5000
does not remove the frontend's separate 5000-row window limit.

Concurrency uses fresh HTTP sessions and a start barrier, with 1, 4 and 8 readers.
Ten waves at each width cycle through the same five request shapes for both
identities. Full responses must equal the validated sequential reference. This
is overlapping requests, not eight complete browser sessions or a long soak.
No writer runs during the measured reader waves.

## Reproduction

Use the ordinary `probe_api_jena.py` arguments with `probe_search_load.py`:
`--java`, `--jar`, a fresh `--output`, `--fasnacht-only`, `--fasnacht-export`,
`--browser-preview`, `--fulltext-preview`. No browser or media service is needed;
the browser-preview fixture supplies the two identities and live fulltext index.
The load wrapper creates `browser-stop` automatically and the owner cleans up
services on success/failure. It writes aggregate samples without credentials or
response content to `search-load-results.json` even if a check fails.

Synthetic inserts are bounded updates inside one transaction per size. The
initial pilot exhausted the test engine's 256 completed-transaction-ID budget
when each update chunk committed separately. This was a fixture setup failure,
not evidence of a search scalability threshold; no server limit was relaxed.

## Results

The corrected `search-load-02` passes **207 load checks**, including all 130
requests in the concurrency waves. All measured HTTP responses are 200. The
normal pre-growth fixture also passes 30 fulltext and 23 export/API checks.
Source SHA-256 is unchanged and all owned services have stopped.

At 12000 synthetic resources (plus the real export), the same workload gives:

| Concurrent requests | Samples | Median seconds | Sample p95 seconds | Maximum seconds |
| --- | ---: | ---: | ---: | ---: |
| 1 | 10 | 4.32 | 7.43 | 7.43 |
| 4 | 40 | 9.01 | 12.61 | 12.96 |
| 8 | 80 | 18.03 | 22.28 | 23.75 |

These are request latencies for broad searches with thousands of matching
resources, not browser page-readiness times or the selective Laterne/Stamm case.
The five shapes are count, sorted 50-row metadata page, date-filtered count,
50-row structured-date page, and 50-row fulltext page. Public/audit shapes have
equal representation at every concurrency level. Sample p95 is the nearest-rank
statistic on a small bounded run, not a service-level guarantee.

Sequential growth examples (public / audit):

| Synthetic resources | Count seconds | Structured-date page seconds |
| --- | ---: | ---: |
| 1000 | 1.19 / 1.32 | 1.44 / 1.72 |
| 4000 | 1.69 / 2.02 | 2.18 / 3.03 |
| 12000 | 3.29 / 3.95 | 5.45 / 7.65 |

All 6000 public and 9000 audit-visible IDs were retrieved in stable 500-row
pages, with title ties, no duplicates, no omissions and an empty page after the
end. A separate 5000-row window returns exactly the expected first 5000 records
(765003 response bytes; 3.15 seconds), while the public total remains 6000.
The API therefore supports complete retrieval beyond the frontend window.
This run does not exercise a browser containing those synthetic objects or
remove the frontend cap. After concurrent readers finish, removing one asserted
role link reduces both identities' counts immediately, despite retained reifiers.

[Aggregate samples and assertions](jena-search-load-results.json) retain the
exact workload and outcomes without tokens or response contents.

## Deep fulltext follow-up

The subsequent [100-row paging rehearsal](jena-search-pagination.md) found Jena
Text's implicit 10000-index-hit cutoff. This historical run validated first
fulltext pages only; its complete traversal and 5000-row window were metadata
queries. It must not be read as fulltext total/deep-page acceptance. Its broad
fulltext timing samples also used the old candidate window. The follow-up removes
that cutoff before permission filtering and tests fulltext counts and late pages.

## Conclusions and remaining gates

Functional correctness passes this bounded test; broad-query latency under load
is not yet satisfactory. Increasing concurrency approximately doubles the median
again at each tested doubling, so this is not evidence of scalable throughput.
The fixture uses a small Java heap and development HTTP server; it does not
establish which component is saturated or predict production hardware results.
No server limits were increased and no runtime optimization was introduced.

The next correctness priority is explicit server-side paging/total counts in the
archive overview instead of silently relying on a 5000-row complete result set.
Its mixed object/media search and sorting need their own design and browser
acceptance. The next performance investigation is completion-time/query profiling
of broad property/date searches at the larger size, rather than another general
cache. Long-running soak, real production data distribution, concurrent writes,
more than two distinct authorization profiles, and GraphDB comparison remain open.
