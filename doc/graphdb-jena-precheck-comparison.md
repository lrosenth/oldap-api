# GraphDB/Jena comparison after dating eligibility optimization

## Method and scope

Repeat of the [original real-data comparison](graphdb-jena-performance.md), after
the [dating precheck](jena-dating-precheck.md). Same immutable Fasnacht export,
six public ArchiveObject page/count requests, 100-row page limit, title ordering,
structured dates, alternating backend order and 1/4/8 synchronized readers.
Jena uses 8192 MiB maximum heap and a fresh owned API/Redis/dataset; GraphDB and
its existing API remain unchanged. No profiler is active during these requests.

All six cases are equivalent under the original comparison rules: resource IDs,
order, metadata and counts agree; only engine-specific fulltext scores are ignored
between engines. Each backend retains exact complete response stability including
its scores. All 312 timed requests return HTTP 200 (156 per backend). Source export
SHA-256 remains 237fcf17a601db3ff25a784d9166bbfe6f94003069025ab0bd0f81978ead80d6.
All owned test services stopped; no runtime edits or deployment in this repeat.

## Mixed workload results

| Readers | GraphDB median / p95 (ms) | Jena median / p95 (ms) | Jena / GraphDB median | Previous 8 GiB Jena median (ms) |
|---:|---:|---:|---:|---:|
| 1 | 57 / 145 | 118 / 367 | 2.08 | 152 |
| 4 | 132 / 265 | 270 / 537 | 2.05 | 331 |
| 8 | 199 / 396 | 488 / 892 | 2.46 | 570 |

Jena medians are ~22%, ~18%, ~14% below the earlier 8 GiB run. These separate-run
differences include host/JIT variation; the preceding same-target ABBA experiment
is the stronger attribution evidence. GraphDB also varied: its previous medians
were 63/130/259 ms versus 57/132/199 ms now. Consequently a lower Jena absolute
latency does not imply the backend ratio improved uniformly at every concurrency.

| Serial case (two samples each) | GraphDB median (ms) | Jena median (ms) |
|---|---:|---:|
| metadata | 100 | 118 |
| count | 36 | 102 |
| dating | 145 | 362 |
| dating_count | 44 | 144 |
| fulltext | 73 | 117 |
| fulltext_count | 28 | 90 |

The metadata page is relatively close (100/118 ms); dating and counts retain
larger differences. Do not infer precise per-case ratios from only two serial
samples. Jena p95 at eight readers remains ~892 ms versus ~911 ms previously;
the faster common pages do not eliminate the slower dated-request tail.

This is still an unequal-deployment, small-data read baseline, not an engine-only
benchmark, sustained capacity test or write/recovery acceptance. Next investigate
actual date hydration and dated/count query work, preserving fresh access checks.

Reproduce with `probe_backend_comparison.py`, `--java-heap-mb 8192` and the
original CLI arguments using a fresh output directory. Aggregate evidence:
[results](graphdb-jena-precheck-comparison-results.json).
