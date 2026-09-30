# Constructor metadata optimization — 2026-09-30

## Outcome

A small serializer change removes repeated constructor introspection during
Redis JSON decoding. It reduces anonymous resource latency by **27%**, 25-item
summary latency by **21%**, and 100-item summary latency by **15%** in the
uninstrumented local Flask-client comparison against the 0.7.23 source baseline.
At 16 active anonymous readers, a separate matching one-worker/four-thread HTTP
experiment achieves **21% more requests/s** and **29% lower p95**.

All **2,408 timed requests** return HTTP 200. All **1,768 timed HTTP workload
responses** match their normalized references. The complete 17-case catalog
also matches between baseline and candidate for both UnknownUser and rosenth
(**34 before/after content comparisons**). Existing named-graph data and native
service process identities remain unchanged. No VM action, package installation,
service restart, cache flush, version bump or publication was performed.

## Implementation and ownership

`oldaplib/src/helpers/serializer.py` previously called `inspect.signature` for
every decoded typed object when rebinding its connection. The new helper caches
only the immutable tuple of supported connection parameter names (`connection`,
`con`), keyed by the constructor callable. It is a process-local LRU bounded to
256 constructors. Replacing a class or its constructor selects fresh metadata;
in-place signature mutation requires explicit metadata-cache clearing/restart.
Concurrent first misses may perform the same pure computation more than once.

Every decode still creates its own objects and injects the current caller's
connection. No mutable model, permissions, response or user connection is cached
as a value. Queries, JSON representation, model freshness and Project snapshot
copy/notification ownership are unchanged. This avoids a broader shared-model
cache and its invalidation/permission consequences.

## Local serial comparison

Twenty samples per case and subject, after warmup, through the same Flask test
client and API source. These are uninstrumented request times, not profile
elapsed times and not measurements of the separately running native API.

| Subject | Operation | Before | After | Reduction |
|---|---|---:|---:|---:|
| unknown | Medium retrieval | 90.8 ms | 66.5 ms | 26.8% |
| unknown | 25 summaries | 102.1 ms | 80.5 ms | 21.1% |
| unknown | 100 summaries | 132.6 ms | 113.1 ms | 14.7% |
| unknown | Fresh Fasnacht model | 216.2 ms | 212.2 ms | 1.9% |
| rosenth | Medium retrieval | 107.3 ms | 84.3 ms | 21.5% |
| rosenth | 25 summaries | 126.5 ms | 107.3 ms | 15.2% |
| rosenth | 100 summaries | 178.5 ms | 157.7 ms | 11.6% |
| rosenth | Fresh Fasnacht model | 241.8 ms | 232.7 ms | 3.8% |

The fresh model endpoint benefits little; its intentional fresh GraphDB read is
retained. Small changes in that case should not be treated as a proven effect.
Anonymous medium CPU time drops from **81.9 to 57.9 ms** per request. Separate
instrumented measurements retain **three GraphDB queries and 42 Redis reads**.
GraphDB HTTP time stays near 8.8/8.7 ms, while the exclusive cache-deserialization
bucket drops from 52.4 to 24.5 ms. This supports a Python-CPU explanation rather
than fewer database operations.

The separate medium cProfile capture falls from **1,476,039 to 1,043,429 function
calls**. Baseline signature inspection runs **5,599 times**, accumulating 79 ms
under profiling; it disappears from the candidate's leading cost table. These
profile times include profiler overhead and are not latency predictions.
Project deepcopy/model reconstruction remains a large cost. Any next change
must preserve independent mutable objects, connection ownership and callbacks.

## Controlled HTTP workload

Two sequential temporary Gunicorn instances on loopback port 8100, each with
one worker and four threads, run the same 1/8/16/1-reader stages for 30 seconds
plus drain. The normal API on 8000 remains running. Both temporary instances
have the read-only test hook and verify their actual serializer source hash
before measurements. Native API/GraphDB/cache process IDs are checked unchanged
and the temporary listener is released after each run.

The workload matches the earlier fixed warm mix: sorted search plus summaries,
resource opening, archive navigation, structured full text and model/list
metadata, with independent anonymous sessions and 0.5–1.5-second think times.

| Active readers | Before requests/s | After requests/s | Before median | After median | Before p95 | After p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.35 | 1.42 | 118 ms | 89 ms | 136 ms | 124 ms |
| 8 | 9.15 | 9.76 | 120 ms | 84 ms | 452 ms | 281 ms |
| 16 | 13.98 | 16.91 | 395 ms | 215 ms | 796 ms | 568 ms |
| 1 (recovery) | 1.35 | 1.40 | 118 ms | 93 ms | 183 ms | 163 ms |

At 16 readers, API CPU is 91.5% before and 88.4% after (100% = one core),
while GraphDB CPU rises from 88.1% to 101.6% as more requests complete. These
service-wide metrics include background work; they are not query-level CPU
attribution. No overload stop threshold is reached. The four-worker/two-thread
VM was not retested with this unpublished change, so these figures do not
predict its exact improvement.

## Runtime qualification and preservation

The on-disk native API Python environment still reports installed distribution
oldaplib 0.7.22, and its source files differ from 0.7.23. To avoid attributing the
previous optimization to this change, both sides explicitly select **0.7.23
source**: a private pre-edit snapshot for baseline and the candidate checkout
for after. Imported source version, path and hashes are recorded independently
of installed distribution metadata. All tracked library source hashes in the
inventory match between sides except the intentionally changed serializer.
Native API timings are excluded from the serial comparison; native responses
are used only for content equivalence. No local installation was silently
upgraded. The private immutable comparison baseline lives in
`/Users/rosenth/.codex/oldap-cpu-20260930/baseline-source`.

All before/after fingerprints across serial, equivalence and HTTP runs retain
**52,490 explicit named-graph bindings**, SHA-256
`22a0fec5fe229ce12513d0c6e4e21c5d38f035df2cbb0365958e9085d7a83b26`.
They cover explicit named graphs, not inferred data, repository configuration or
an independent default graph. The current data differ from the previous day's
baseline; only this iteration's unchanged data are used for its comparisons.
All database traffic is through the existing bounded read guard/read routes.
No destructive integration fixtures were invoked.

Response normalization treats RDF/model arrays as unordered and media tokens by
presence. Four model-list ordering differences versus the native API already
occur in baseline and recur for candidate; their normalized contents match.
The eight HTTP workload reference hashes match across both source versions.

## Validation, reproduction and release boundary

- **101 focused offline checks pass:** 70 library, 14 API read/auth/startup,
  and 17 read-tool tests. Library/API checks reject unexpected HTTP transport.
- New regressions cover both connection keyword names, classes without either,
  replacement/re-registration, bounded retention, threaded caller separation,
  independent nested payloads and real Project JSON roundtrips.
- Raw private artifacts: `/Users/rosenth/.codex/oldap-cpu-20260930`.
- [Aggregate JSON](2026-09-30-serializer-summary.json),
  [serial comparison CSV](2026-09-30-serializer.csv).
- Reproduction: select baseline/candidate with `PYTHONPATH`; run
  `tools/read_performance.py --catalog PRIVATE_CASES --output NEW_DIRECTORY
  --samples 20 --mode inprocess --mode instrumented` with the four report cases.
  Use `--verify-only` without case filters for all 17 routes, then
  `tools/worker_read_experiment.py --catalog PRIVATE_CASES --output NEW_DIRECTORY
  --workers 1 --seconds 30`. See [README](README.md) for the safety boundary.

Publish a new oldaplib release and update the consumers through the normal
release workflow before activating this change outside the source experiments.
Then repeat the accepted VM full-batch catalog with unchanged worker settings.
A short warm local A/B run is not a sizing guarantee, long-duration soak test,
HMB data-growth test or justification for async/Enterprise migration.
