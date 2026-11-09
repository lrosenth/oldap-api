# Archive overview latency breakdown — 2026-11-09

## Main result

The browser waits mainly for backend work. Nine search requests are issued once,
plus three taxonomy reads, public authentication and the public-user lookup.
The page starts these reads together and awaits the resulting group. The dated
CarnivalThing search is the critical request in the measured final browser runs.

| Measurement | Local | Production |
|---|---:|---:|
| DOM-ready overview, three fresh contexts | 0.961–1.041 s | 3.947–4.382 s |
| Median DOM readiness | 1.004 s | 4.074 s |
| Browser main-thread task time | about 0.1 s | 0.15–0.16 s |
| Object/event search, 437 rows, isolated serial request | 481 ms | 1557 ms |
| Small Agent search, isolated serial request | 89 ms | 402 ms |
| Media preview metadata search | 120 ms | 401 ms |
| Public media projection | 122 ms | 404 ms |

Three production samples per exact search payload were replayed from inside the
API container over loopback. Thus these serial server times exclude the user's
VPN/browser network. Browser bursts make many otherwise 0.3–0.5 s requests take
roughly 2–3 s: queueing/shared-resource contention and repeated work are material.
Their exact split has not been instrumented on production. Reads are not forced
through the single writer: JenaSessionEngine dispatches READ under a shared read
lock and a TDB read transaction. More parallel requests are not automatically faster.

## Jena versus Python

Four unprofiled local repetitions after a warmup, using the nine exact public
search payloads captured from the current production frontend:

| Component | Sum per nine searches | Share |
|---|---:|---:|
| Jena dispatch: parse, evaluate and serialize | 808 ms | 68.2% |
| Python outside backend HTTP waits | 292 ms | 24.6% |
| Jena identity callback authentication | 46 ms | 3.9% |
| Remaining backend HTTP/transfer/scheduling | 40 ms | 3.4% |

These are **sums of serial API work**, not additive portions of the parallel
browser's wall time. Jena dispatch is broader than pure SPARQL evaluation. Normal
searches make three backend calls; the dated search makes fifteen, for 39 calls
across the nine searches. cProfile was collected in separate runs because it
roughly doubles the dated request; its times are not used in the latency table.

### Dates are a distinct expensive stage

The 437-row CarnivalThing search takes locally about 481 ms: 269 ms Jena dispatch,
171 ms Python, and roughly 32 ms callback/transport plus small HTTP overhead.
The nested date-expansion span is about 351 ms and must not be added again.
It reads five batches (100/100/100/100/37) using CONSTRUCT, repeatedly resolves
external prefixes and builds structured summaries. Its fifteen backend replies
total about 1.14 MB for one API request. CPU profiles identify graph conversion,
QName processing and model/property deepcopy work, not just JSON encoding.

An alternating eight-request local control retained the same row order and all
non-date values. Median latency was 458 ms with dates and 121 ms without dates.
This isolates about 337 ms (74% of that request) associated with requesting dates;
it is **not** a proposal to remove dates or a promised page-level speedup.

### Repeated broad searches are the other main target

Even tiny Agent/Person/Organisation results spend most of their local time in
one SELECT. The generated query independently builds class candidates and readable
resources through role grants, then joins them. Many overview requests repeat
this similar authorization/search work. The profile identifies the SELECT as
expensive; it does not yet isolate the ACL join from class resolution/other
operators. A class-restricted query-plan comparison is the next evidence step,
not grounds to remove permission checks or hardcode Fasnacht classes.

## Recommended next steps

1. Investigate the shared search SELECT plan on this isolated target. Compare
   earlier class/candidate restriction with the current role-grant plan, preserving
   complete rows/order and testing public, restricted and administrative readers.
   This may benefit most overview searches without introducing a frontend cache.
2. Simplify date hydration: avoid repeated model copies/prefix discovery within
   one request and examine a narrower permission-aware date batch. Retain live
   ontology declarations, date semantics and existing API/function signatures.
3. Only after reducing that work, compare a bounded request fan-out or shared
   metadata reads. Consider real paging separately: the frontend still retrieves
   665/666 media and all 437 objects/events (limits are 5000). A cosmetic LIMIT 100
   would change grouping, filter completeness and counts.

The largest measured opportunities are backend query work and date hydration.
Browser rendering and ordinary network transfer are not leading candidates here.
No additional memory or worker-count change is justified by these measurements.

## Reproduction and limits

`tools/migration/profile_archive_page.py` accepts the normal owned preview CLI
plus `--cases` containing captured public search paths/bodies. It wraps requests
and Flask dispatch with request-local timing, asks only the isolated probe for
native timing headers, and retains separate CPU profiles and generated SPARQL.
Use `--fasnacht-only --browser-preview --fulltext-preview --fasnacht-export`,
Java 25 and the pinned Fuseki 6.2.0 JAR; this hook measures plain searches and does
not claim fulltext-index acceptance. A fresh output directory is required.

Private commands, cases, browser observer, query texts and profiles are retained
under `OLDAP-Jena/probes/archive-breakdown-20261109` in Application Support.
The browser uses a local production build, not Vite development mode. Readiness
is recorded by a DOM observer; locator polling initially inflated times by about
0.4 s. Final request event timestamps are monotonic; one preliminary browser
wall-clock waterfall was inconsistent and is not used for attribution.

The local export is from November 2: 665 media versus 666 in production, 26 versus
27 agents, and different date payloads; the 437 object/event count matches.
Local uses a threaded native API and 8 GiB Java heap, production Gunicorn/containers
on a different VMware/Intel host. This is diagnostic attribution, **not** a matched
hardware/engine benchmark or a proof of production percentages. Fresh browser
contexts do not imply a cold database/model cache. No production instrumentation,
service restart, runtime optimization, data edit or deployment was performed.
