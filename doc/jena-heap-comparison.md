# Jena heap-size follow-up

The user requested a generous Java memory allocation on the 36 GiB test host.
The owned API fixture now accepts `--java-heap-mb` (default 512). The follow-up
uses 8192 MiB, then a fresh 512 MiB control with the same six-case benchmark.
Only the owned server's maximum heap changes. Xms remains JVM-controlled;
conversion subprocesses, source GraphDB, query code and service settings do not
change. Allocating a higher ceiling does not force use of the entire heap.

## Method

Reuse [the real-data baseline](graphdb-jena-performance.md), including all result,
ordering, permission-scope and source-export checks. Each run recreates the target
and managed text index from the same source/YAML, warms the same requests, and
alternates GraphDB/Jena execution. Each measures 312 requests across 1/4/8 readers.
No extra profiling is performed during timed waves. The fresh 512 MiB control
helps distinguish a heap effect from ordinary host/JIT variation; this remains a
small sequential experiment, not a randomized repeated capacity study.

The 8 GiB JVM was verified with `jcmd VM.flags` before benchmark timing:
`MaxHeapSize=8589934592`, G1 GC. A setup-time heap snapshot used approximately
135 MiB; that is neither steady-state usage nor a peak measurement. A larger Xmx
also changes JVM ergonomics, so this experiment measures the resulting JVM
configuration rather than memory capacity independently of garbage collection.

## Reproduction

Use the baseline command, adding `--java-heap-mb 8192` and a fresh output directory.
Repeat with `--java-heap-mb 512` and another fresh directory. The runner records the
heap ceiling in its sanitized results; `java-process.json` in private output also
records the owned PID for diagnostics. No permanent service is reconfigured.

## Results (2026-11-02)

Both runs pass all six cross-backend cases and all 312 timed requests each
(624 total, 312 Jena and 312 GraphDB). Results retain exact per-backend response
stability, source export hashes are unchanged, and owned services are stopped.

| Readers | Fresh 512 MiB median / p95 (ms) | 8 GiB median / p95 (ms) | Median reduction |
|---:|---:|---:|---:|
| 1 | 156 / 406 | 152 / 385 | 3.2% |
| 4 | 341 / 559 | 331 / 547 | 2.9% |
| 8 | 591 / 923 | 570 / 911 | 3.6% |

The 8 GiB run is only 2.9–3.6% faster on median latency than the fresh small-heap
control. The original 512 MiB medians were 164/315/579 ms; the 8 GiB run is not
uniformly faster than that older baseline. No substantial memory-related speedup
is demonstrated for this small real-data workload. Small differences are not
statistically established with one fresh run per setting. GraphDB medians also
vary between runs; all GraphDB raw samples remain in the attached reports.

This does not establish that 512 MiB suffices for larger datasets or sustained
production load. Nor does it measure peak memory or garbage-collection pressure.
Increasing only Xmx to 8 GiB does not close the API performance gap here.
Keep the historical probe default for reproducibility; use explicit heap settings
for future capacity studies. Profile query, transport and API costs next.

Evidence: [8 GiB results](jena-heap-8g-results.json),
[fresh 512 MiB results](jena-heap-512m-control-results.json).
The control JVM was also verified with MaxHeapSize=536870912 and G1 GC.
CLI help, compilation, nonpositive-heap rejection before side effects and diff
checks pass. No production setting, public API or library behavior changed.
