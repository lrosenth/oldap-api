# Read-path optimization: measured before/after — 2026-09-29

## Outcome

The optimized library is active in the local native API. Representative public resource and metadata requests have **73–85% lower median latency** (about **3.7–6.7 times faster**) in the repeated catalog. Both implementation changes were measured together; this is not a separate causal A/B estimate for each change.

The strongest evidence is the combination of unchanged responses, identical request catalogs/data, reduced Redis operations, and improved live HTTP latency. Small differences in already-fast searches remain noisy and should not be treated as a general speedup.

## Live HTTP comparison

Times are medians in milliseconds for `unknown`. Main cases: n=12 before and after. The model and Lucene-field cases use n=6. Raw p95/maxima and the separate administrator comparison are in the linked CSV/JSON.

| Case | Before ms | After ms | Reduction | Speedup |
|---|---:|---:|---:|---:|
| Open person | 617.0 | 100.0 | 83.8% | 6.17× |
| Open archive medium | 515.0 | 97.4 | 81.1% | 5.29× |
| Open linked archive unit | 510.1 | 121.6 | 76.2% | 4.20× |
| First 25 search hits | 37.3 | 24.1 | 35.5% | 1.55× |
| Sorted search | 38.3 | 30.3 | 20.8% | 1.26× |
| Sorted search, offset 250 | 39.0 | 35.5 | 9.0% | 1.10× |
| Count results | 34.7 | 31.1 | 10.4% | 1.12× |
| Broad fulltext | 37.6 | 31.5 | 16.1% | 1.19× |
| Search with name/description | 38.2 | 32.6 | 14.6% | 1.17× |
| 25 metadata summaries | 757.7 | 112.4 | 85.2% | 6.74× |
| 100 metadata summaries | 548.2 | 147.8 | 73.0% | 3.71× |
| 25 summaries + media delivery | 540.1 | 114.2 | 78.9% | 4.73× |
| Browse archive children | 19.4 | 22.4 | -15.7% | 0.86× |
| Read hierarchical list | 32.1 | 29.7 | 7.5% | 1.08× |
| Fasnacht UI datamodel | 464.6 | 226.1 | 51.3% | 2.05× |
| Shared UI datamodel | 167.8 | 102.4 | 39.0% | 1.64× |
| Lucene title/description query | 25.9 | 25.7 | 0.7% | 1.01× |

Archive-child browsing is slightly slower in this run (19.4 → 22.4 ms); this small absolute difference is not hidden. The no-cache broad fulltext path also varies, illustrating why modest search differences cannot be attributed entirely to this optimization. The large resource-path improvement is reproduced in the supplement: medium 460.3 → 95.2 ms and 25 summaries 535.1 → 110.3 ms.

## Mechanism and remaining cost

For a warm medium read, Redis GET/command count falls from **563 to 42** (92.5% fewer). Warm requests create **zero Redis clients**, versus 1,126 previously in the refined baseline. The previously measured 563 connection setups disappear from the warm profile. The three GraphDB queries and permission filtering remain unchanged.

Project.read is still invoked 524 times by model constructors, but repeated invocations now copy short-lived resolved snapshots rather than fetching and deserializing project JSON again. Three distinct project snapshots are populated through normal Redis cache reads; the other reads reuse snapshots. The remaining Redis reads primarily reconstruct other model components.

The instrumented medium mean changes from 595.2 to **98.1 ms**. In the new run:

| Timing bucket | Mean ms | Interpretation |
|---|---:|---|
| Factory construction (inclusive) | 84.8 | Still the main remaining cost, including model/project work below |
| Redis commands (exclusive) | 4.0 | 42 operations using existing connections |
| Cache get remainder (exclusive) | 52.2 | Python model reconstruction, excluding measured child spans |
| Project.read remainder (exclusive) | 23.0 | Independent snapshot copies and project handling |
| GraphDB HTTP (exclusive) | 10.5 | Three queries including wait/evaluation/transfer |

The inclusive factory row overlaps the exclusive rows and must not be added to them. The earlier refined Redis bucket was 384.4 ms; observed before/after transport differences also include run-to-run noise. Separate cProfile runs reduce roughly 4.0 million function calls to 1.47 million. The remaining profile highlights object reconstruction, repeated inspect.signature calls and project deepcopy. These are candidates for a later measured iteration, not implemented promises.

## Implementation

1. **Redis transport reuse:** `cachesingleton.py` retains thread-safe Redis clients/pools keyed by exact URL. There are at most eight retained configurations, each allowing 32 connections. A lock serializes creation; forked children reset inherited clients/locks. Eviction does not explicitly close clients still borrowed by wrappers. No domain objects or permission contexts are stored globally.
2. **Writer-store protection:** `mutation_gate.py` uses redis-py URL parsing to recognize distinct database numbers before constructing a writer client. Same-database configurations still require fresh server identity checks. Isolation is rechecked on every wrapper construction and before any cache flush.
3. **Project snapshot reuse:** `project.py` scopes snapshots using ContextVar to synchronous model construction. `DataModel.read` and `ResourceInstanceFactory.__init__` establish/reuse the scope for one connection. Each caller receives a separate copy with its own notifier/change tracking; no long-lived connection memo or cross-request model cache. ignore_cache=True bypasses snapshots and updates them after a successful fresh read.
4. **Copy correctness:** Project.__deepcopy__ now copies the actual `_changeset` attribute (fixing the prior `_changset` typo) and rebinds notifiers to the copy. The caller connection is preserved explicitly for scoped snapshots.
5. **Reproducibility:** the diagnostic accepts `--catalog` to replay saved requests exactly, records installed source hashes, and performs the normal anonymous bootstrap outside timings after a fresh API start.

No GraphDB query, role assignment, RDF data/model, public API contract or JSON cache wire format was changed. The model endpoint retains its authoritative ignore_cache=True behavior.

## Validation and data integrity

- 39 focused library tests pass, including 10 new offline pool/snapshot regressions, existing isolated Redis writer-gate tests, list-context and resource/query tests.
- 10 API authentication/resource-summary tests and four benchmark safety/accounting tests pass: **53 targeted tests total**. No destructive GraphDB integration fixtures were executed.
- Before activation, all 34 content comparisons between the original live API and optimized source match. RDF/model arrays are normalized as unordered; independently issued media JWT values are excluded while their presence is retained.
- After activation, all 34 installed/isolated content comparisons also match.
- After activation, the same 1,188 timed requests complete with HTTP 200, replaying the exact old baseline/supplement catalogs. Warmups and verification calls are additional, untimed requests.
- Explicit named-graph fingerprint is unchanged across original baseline, pre-activation comparison, deployment and both post-optimization runs: **52,471 bindings**, SHA-256 `ebaaeac52dc4309166aa17747a71b6a566d51ffe8aa7d86cf078d520751eaaa4`.
- The API was restarted using its existing writer-gated make restart, and the gate was released successfully. Its standard startup cleared only the normal object cache; no GraphDB or writer-store reset. Both reported baselines are warm.

## Local activation and rollback

The native API uses an **unpublished local development wheel still labelled oldaplib 0.7.22**. No package release or production deployment was made. The five installed source files are byte-identical to the optimized checkout; their SHA-256 hashes are in the measurement inventories and activation record. Do not identify this build by version number alone.

Previous installation backup and activation identity: `/Users/rosenth/.codex/backups/oldap-performance-before-optimization/`. The archive contains the prior oldaplib package and matching dist-info. To roll back, restore those archived directories into the recorded native API site-packages directory and use the same writer-gated API restart. Do not reset a busy/retained writer gate.

## Limits and next decision

Unchanged limits from the first report apply: local small dataset, serial fixed requests, warm caches, 12/6 samples, no browser/WAN/image transfer, no concurrency or HMB sizing. p95 is effectively the maximum of these small samples. Before/after runs are sequential; they are not randomized experiments. Both changes were activated together.

The bounded pool is per process/configuration, not a user-count limit. More than 32 simultaneous checked-out connections raises redis-py ConnectionError. Validate the pool bound alongside API workers in a future load test rather than assuming unlimited scaling. The snapshot scope is explicitly synchronous and must be revisited for any async conversion.

The next strategic experiment should be the planned mixed-user concurrency test. Single-request factory cost remains measurable at approximately 85 ms; immutable model metadata/serializer inspection reuse can be considered separately if the application latency target requires another reduction. FastAPI and Enterprise/core comparisons still need their own workload measurements.

## Evidence and reproduction

- [Original report](2026-09-29-baseline.md)
- [Comparison CSV](2026-09-29-comparison.csv) and [comparison JSON](2026-09-29-comparison.json)
- [Optimized aggregate timings](2026-09-29-optimized-summary.json)
- [Measurement instructions](README.md)

Private raw artifacts:

- `/Users/rosenth/.codex/oldap-performance-optimized-equivalence` — original live vs optimized source.
- `/Users/rosenth/.codex/oldap-performance-after-optimization-run2` — complete 1,008-request replay, 23:41:10–23:43:10 Europe/Zurich.
- `/Users/rosenth/.codex/oldap-performance-after-optimization-supplement` — 180-request replay, 23:43:21–23:43:57.
- `/Users/rosenth/.codex/oldap-performance-after-optimization-verify` — installed runtime vs isolated runtime.

The first post-restart attempt (`oldap-performance-after-optimization`) is excluded: the native process had no project-prefix context before an ordinary anonymous login, so the first measured read returned 404 and the run stopped with zero accepted samples. The replay now performs that normal bootstrap outside timing. This pre-existing cold-process behavior is not a performance improvement or a regression in the changed code.
