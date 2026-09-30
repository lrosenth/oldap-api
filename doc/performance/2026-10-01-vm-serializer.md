# Deployed serializer optimization: VM comparison — 2026-10-01

## Outcome

The deployed **API 0.2.30 / oldaplib 0.7.24** contains the exact serializer
implementation tested locally. With unchanged **four-worker/two-thread** settings,
representative warm resource and summary medians improve by **19–30%** against
the previous **API 0.2.29 / oldaplib 0.7.23** VM baseline.

The accepted run completes **1,132 timed HTTP-200 reads** without content errors:
204 serial requests and 928 mixed-workload requests. All **17 reference response
hashes**, the exact request catalog and the explicit named-graph fingerprint
match the previous complete-batch VM baseline. Summary responses still contain
25 / 100 / 25 resources (last variant includes delivery metadata).

At 16 active readers, the median falls **232→167 ms**, p95 **649→591 ms**,
and throughput rises **16.13→17.03 requests/s**. API CPU falls **2.13→1.78 cores**
while serving more requests. This is chiefly a latency/CPU-efficiency improvement;
closed-loop think time limits the throughput gain to about 6% in this workload.
It is not a maximum-capacity or HMB-sizing result.

## Serial comparison

Twelve samples per case following discarded warmup; medians below exclude JSON
parsing/content hashing and public proxy/TLS/WAN overhead. The before values
come from the previous VM's **complete-batch** catalog, not its initial partial
15/60-resource replay.

| Operation | Before | After | Reduction |
|---|---:|---:|---:|
| Medium retrieval | 185.2 ms | 129.5 ms | 30.1% |
| Linked archive retrieval | 193.6 ms | 137.9 ms | 28.8% |
| 25 summaries | 213.6 ms | 155.5 ms | 27.2% |
| 100 summaries | 275.4 ms | 222.7 ms | 19.1% |
| 25 summaries + delivery | 223.8 ms | 169.2 ms | 24.4% |
| Sorted search | 29.2 ms | 30.3 ms | -3.5% |
| Structured full text | 38.7 ms | 39.3 ms | -1.7% |
| Fresh Fasnacht model | 448.8 ms | 432.6 ms | 3.6% |

Searches and fresh model reads change relatively little; their small differences
are not sufficient evidence of a separate improvement/regression. The serializer
change specifically reduces reconstruction work on the cached model path.

## Mixed-reader comparison

Same 1/8/16/1-reader sequence, 30 seconds per stage plus drain, independent
anonymous sessions and 0.5–1.5-second think time. Same fixed search+25-summary,
resource, archive, full-text and model/list workflows. No worker count or thread
setting was changed. Only the serial cases include 100-resource summaries.

| Active readers | Before requests/s | After requests/s | Before median | After median | Before p95 | After p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.28 | 1.31 | 193 ms | 132 ms | 318 ms | 257 ms |
| 8 | 8.97 | 9.53 | 191 ms | 141 ms | 454 ms | 388 ms |
| 16 | 16.13 | 17.03 | 232 ms | 167 ms | 649 ms | 591 ms |
| 1 (recovery) | 1.33 | 1.31 | 190 ms | 135 ms | 301 ms | 269 ms |

At 16 readers, API CPU changes from 213.2% to 178.4% (100% = one core), and
GraphDB from 32.7% to 36.9%. API peak summed RSS is about 521 MiB versus 524 MiB;
GraphDB is near 1,871 MiB in both runs. These service-wide metrics include other
traffic/background work; summed RSS can count shared pages more than once.
Recovery returns to the initial single-reader median range. The longest timed
request in the 16-reader stage is 848 ms; no latency/error stop threshold fires.

This is a sequential before/after comparison on a shared VM, not a randomized
experiment or a statistically established production SLA. Tail latency is
sensitive to workload/worker distribution and short-run noise. The strongest
combined evidence is the serializer source match, unchanged inputs/results,
repeatable serial gains and lower CPU demand. The earlier one-worker laptop
throughput gain should not be transferred directly to this four-worker VM.

## Acceptance and measurement correction

The first attempt completed serial reads and the 1/8/16-reader stages without
response errors but failed its process-list guard during final recovery.
Inspection retained exactly the initial Gunicorn/master, Java and Redis PIDs;
API lifecycle logs showed no worker restart. The old sampler counted every
container process, including transient healthcheck and read-only `docker exec`
helpers. The exact triggering helper was not captured, so its identity cannot
be asserted retrospectively.

The sampler now selects the deployed `gunicorn`, `java` and `redis-server`
processes, requires each service to exist, and still rejects actual PID changes.
Mismatch diagnostics retain expected/observed IDs. New offline regressions check
helper exclusion and missing-service rejection; **19 read-tool tests pass**.
The first attempt remains private evidence and is **excluded from acceptance**.
The complete repeated run, with identical request/timing logic, supplies all
reported after values. No application or deployment code was changed by this fix.

Public HTTPS smoke reads for a resource, sorted search and 25 summaries all
return HTTP 200 and match the VM-local reference contents. Array normalization
ignores order and compares media capabilities by presence; no token or complete
response body is persisted.

## Data preservation and release identity

Before/after both attempts, and after public smoke checks:
**50,396 explicit named-graph bindings**, SHA-256
`d497d294b6f5132f4eac4bf34d755b438043533604d2557a36eaecdd95922cdc`.
The fingerprint matches the previous VM baseline. It is a fixed read-only
SELECT over explicit named graphs; inferred statements, repository settings
and an independent default graph are outside its coverage.

Serializer SHA-256 in the deployed image:
`d84cad74cf5212606554308b9328afe67e919c2d1129793be294cbb8d2aa48b7`.
This matches the accepted local optimization. Between library tags 0.7.23 and
0.7.24, runtime source changes are the serializer and version marker; API tags
0.2.29→0.2.30 do not change endpoint implementation. Effective package versions
are captured in the aggregate JSON. Checking running code was necessary: an
earlier deployment still contained the old library despite the updated lock.

No GraphDB writes, cache clearing, configuration edits, worker changes, recovery
faults or service restarts were performed during measurement. API/GraphDB/cache
container identities and service PIDs remain unchanged. The private temporary
VM directory was removed after retrieving both attempts and verification data.

## Artifacts and next step

- [Aggregate JSON](2026-10-01-vm-serializer-summary.json),
  [serial comparison CSV](2026-10-01-vm-serializer.csv).
- [Previous VM baseline](2026-09-30-vm.md), [local source comparison](2026-09-30-serializer.md).
- Private raw artifacts: `/Users/rosenth/.codex/oldap-vm-read-20261001`;
  `results` is incomplete, `repeat-results` is the accepted run.
- Reproduction: [README](README.md#existing-docker-vm-measurement), using the
  saved VM catalog and `--seconds 30 --users 1 8 16 1`.

Keep four workers/two threads. The next measured library candidate is independent
Project/model reconstruction and copying; retain permission and mutation
isolation. This workload supplies no reason by itself to change GraphDB edition
or migrate frameworks. Larger representative data and long-running traffic
remain separate sizing work.
