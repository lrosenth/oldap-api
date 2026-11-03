# GraphDB versus Jena: real-data read baseline

This is a bounded comparison of the existing GraphDB-backed API and the current
Jena-backed API, not a controlled engine-only benchmark or production sizing test.
The runner is `tools/migration/probe_backend_comparison.py`.

A subsequent [512 MiB versus 8 GiB heap experiment](jena-heap-comparison.md)
reuses this workload with a fresh small-heap control.

## Method and safety

- Fresh native TriG-star export of the four Fasnacht project graphs, `infer=false`.
  SHA-256: `237fcf17a601db3ff25a784d9166bbfe6f94003069025ab0bd0f81978ead80d6`.
  The 6,578,599-byte export matches the earlier real-data rehearsal. Private source
  files and process logs stay outside Git. The source export is hashed again after
  the workload; this is a byte-stability check, not a transactional backup protocol.
- Existing GraphDB Desktop/API at localhost:7200/8000 are read only. No source
  model/data changes, cache flushing, service restart or synthetic population.
  Authentication and ordinary server logging still occur.
- Target: existing owned migration fixture, converted data, current Fasnacht YAML,
  current Jena API/lib, actual isolated Redis and 512 MiB Java heap. Its internal
  synthetic CarnivalEvent fixture does not belong to the ArchiveObject workload.
  All target processes are stopped by the owning runner, including on failure.
- Same machine (Mac17,7, 18 logical CPUs, 36 GiB RAM). GraphDB API is the existing
  Python process rooted in OLDAP/oldap-api; target uses a fresh threaded Werkzeug
  server. GraphDB heap, reasoner materialization, caches, JVM history and other
  repositories differ. Existing unrelated local services are not stopped.
- Public identity only. Six POST cases: ArchiveObject metadata page/count,
  dating page/count (1900–1999 overlap), title fulltext page/count (`Laterne`).
  Pages explicitly sort by title and use limit 100; structured dating requested.
- Before timing: compare statuses, counts, page order, resource classes and all
  projected values. RDF multivalue order is ignored. Engine-specific relevance
  scores are excluded only from cross-engine comparisons of title-sorted pages;
  each backend must reproduce its own complete response, including scores.
  Non-equivalent cases are excluded from speed comparisons and explicitly recorded.
- One additional warm-up per case/backend. Twelve mixed-workload waves per
  concurrency level (1, 4, 8), alternating backend execution order. Independent
  HTTP sessions and synchronized starts; 30-second HTTP timeout. No cold-cache
  claim. Throughput includes wave startup; it is not saturated-server throughput.
- Six-case serial medians have only two samples each. Mixed-workload p95 is the
  nearest-rank empirical quantile, not a confidence bound. Repeating this on equal
  isolated deployments is needed before attributing a difference to either engine.

## Results (2026-11-02)

All six cases agree after excluding engine-specific fulltext scores. The other
five complete responses agree without that exclusion. Counts: 422 public archive
objects, 229 dating matches, five title-text matches. All 312 timed requests
(156/backend) return HTTP 200 and preserve each backend's reference response.
Source export is unchanged; the owned API, Java and Redis processes have stopped.

| Concurrent requests | GraphDB median / p95 (ms) | Jena median / p95 (ms) | GraphDB / Jena requests/s |
|---:|---:|---:|---:|
| 1 | 61 / 161 | 164 / 363 | 13.65 / 5.70 |
| 4 | 128 / 240 | 315 / 523 | 18.69 / 8.58 |
| 8 | 205 / 904 | 579 / 917 | 16.94 / 9.11 |

| Serial case (two samples each) | GraphDB median (ms) | Jena median (ms) |
|---|---:|---:|
| metadata | 87 | 178 |
| count | 36 | 89 |
| dating | 156 | 355 |
| dating_count | 48 | 146 |
| fulltext | 75 | 196 |
| fulltext_count | 37 | 88 |

For this bounded workload, GraphDB has lower median latency; Jena is about
2.5–2.8 times slower on the mixed workload. Both remain below one second at
the empirical p95, including eight concurrent readers. This is encouraging
functional parity but not performance parity. Profile API/transport/query time
on the same cases before changing code; do not compensate with permission caches.

The preliminary run excluded fulltext pages because raw relevance scores differed.
The final run compares all actual projected data and ordering while retaining
strict per-engine score stability. Only the final six-case run is tabulated.
Raw sanitized timings: [results](graphdb-jena-performance-results.json).
Fingerprint checks verify unordered RDF values, ordered result pages, exact
counts and the narrowly scoped score exclusion. Python compilation and diff checks pass.

## Reproduction

From the Jena API checkout, use its virtualenv Python. First export into a new
private directory with `tools/migration/export_fasnacht_readonly.py --output ...`.
Then run:

```sh
.venv/bin/python tools/migration/probe_backend_comparison.py \
  --java /absolute/path/to/java \
  --jar /absolute/path/to/fuseki-server.jar \
  --output /absolute/path/to/new-private-result-directory \
  --fasnacht-only --fasnacht-export /absolute/path/to/source.trig \
  --browser-preview --fulltext-preview
```

The preview callback performs the comparison and automatically requests shutdown.
The source endpoints and project scope are deliberately fixed to the existing local
Fasnacht setup. Do not use this runner for unbounded or write load on a shared server.

## Remaining scope

Authenticated role parity, complete traversal/deep offsets, media classes, linked
fulltext fields, multiword/accent semantic differences, real sustained traffic,
concurrent writers, equal heap/CPU deployments and synthetic scale on BOTH backends
remain separate work. Existing Jena-only 12,000-resource results cannot be compared
directly with this real-data baseline. No application runtime/API signature changed.
