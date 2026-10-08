# Deployed project identity optimization — 2026-10-01

## Outcome

The user-deployed **API 0.2.31 / oldaplib 0.7.25** contains the exact Project and
PropertyClass implementations measured locally. The VM retains **four Gunicorn
workers with two threads each** on eight vCPUs. Compared with the preceding
API 0.2.30 / oldaplib 0.7.24 VM run, resource medians improve **10–13%** and
metadata-summary medians **4–10%**.

The complete run returns **1,152 successful timed reads**: 204 serial reads and
948 mixed-workload reads. All 17 normalized reference contents, full metadata
batch sizes and the request catalog match the previous VM run. No data writes,
cache clearing, deployment, configuration edits or restarts were performed.

## Serial comparison

Twelve measured anonymous reads after one discarded warmup per case, using the
same complete-batch VM catalog. HTTP durations exclude JSON parsing/hashing and
public proxy/TLS/WAN overhead. The baseline is the accepted `repeat-results`
run documented in [the serializer VM report](2026-10-01-vm-serializer.md).

| Operation | Before | After | Reduction |
|---|---:|---:|---:|
| Person retrieval | 130.7 ms | 113.2 ms | 13.4% |
| Medium retrieval | 129.5 ms | 116.4 ms | 10.1% |
| Linked archive retrieval | 137.9 ms | 122.0 ms | 11.5% |
| 25 summaries | 155.5 ms | 148.9 ms | 4.2% |
| 100 summaries | 222.7 ms | 203.2 ms | 8.8% |
| 25 summaries + delivery | 169.2 ms | 151.4 ms | 10.5% |
| Sorted search | 30.3 ms | 32.9 ms | -8.6% |
| Structured full text | 39.3 ms | 42.5 ms | -8.0% |
| Fresh Fasnacht model | 432.6 ms | 443.9 ms | -2.6% |

All summary variants still return 25 / 100 / 25 resources. Search cases are
roughly 2–4 ms slower this time and fresh model reads slightly slower; this
short sequential comparison cannot attribute those differences to the change.
There is no demonstrated search or fresh-model improvement. The observed
resource gain supports the local finding, but does not establish a universal
15–20% latency reduction.

## Mixed readers

Identical 1/8/16/1-reader stages, 30 seconds each plus drain, with independent
anonymous sessions and 0.5–1.5-second think time. The workload retains its fixed
resource, search/25-summary, archive, full-text and model/list workflows. Only
serial cases include 100-resource batches.

| Readers | Before requests/s | After requests/s | Before median | After median | Before p95 | After p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.31 | 1.35 | 132 ms | 118 ms | 257 ms | 191 ms |
| 8 | 9.53 | 9.45 | 141 ms | 120 ms | 388 ms | 373 ms |
| 16 | 17.03 | 17.40 | 167 ms | 143 ms | 591 ms | 559 ms |
| 1 (recovery) | 1.31 | 1.31 | 135 ms | 119 ms | 269 ms | 289 ms |

At 16 readers, median latency improves about **15%**, p95 about **5%**, and
throughput only **2%**. API CPU falls **178.4% → 156.5%**, where 100% is one core;
GraphDB CPU remains **36.9% → 36.7%**. These are service-wide metrics, including
unrelated traffic/background work. Think time bounds offered load, so these
results measure reduced latency/CPU demand rather than maximum capacity.

Recovery returns to the initial single-reader median. Its p95 is higher than
the baseline, illustrating short-run tail variability. All stages finish with
zero errors and no stop threshold reached; the longest 16-reader request is
962 ms. This is one sequential shared-VM comparison, not a randomized experiment,
SLA, HMB sizing exercise or justification for changing GraphDB edition/framework.

## Acceptance, source identity and data preservation

- Runtime packages: API 0.2.31, oldaplib 0.7.25, Flask 3.1.3, Gunicorn 26.0.0,
  requests 2.34.2, Redis client 7.4.0, rdflib 7.6.0.
- Deployed `project.py` SHA-256:
  `4892eb5f67e0cc2967dd75ef84ce2331fa83277fe664850d2830c3635673d12c`.
- Deployed `propertyclass.py` SHA-256:
  `483ca8a1f43d23d34a7a94507a936fd9e9c25b2689d2763a6d14939527da1331`.
- Serializer SHA-256 remains
  `d84cad74cf5212606554308b9328afe67e919c2d1129793be294cbb8d2aa48b7`.
- Library release-tag differences contain only Project/PropertyClass runtime
  changes plus version metadata, tests and documentation. API endpoint source
  is unchanged between v0.2.30 and v0.2.31.
- All 17 normalized response hashes match the baseline; each timed workload
  response also matches its reference. Normalization treats arrays as unordered
  and media capabilities by presence, not byte-for-byte equality.
- Public HTTPS medium, sorted-search and 25-summary reads return 200 and match
  VM-local contents. Tokens and complete responses remain in memory.
- Before/after the run and after public checks: **50,396 explicit named-graph
  bindings**, SHA-256
  `d497d294b6f5132f4eac4bf34d755b438043533604d2557a36eaecdd95922cdc`,
  identical to the prior VM baseline. Inferred data, settings and an independent
  default graph are outside fingerprint coverage.
- API/GraphDB/cache container identities and service PIDs remain unchanged.
  The separate post-run verifier excludes the terminated load-client PID when
  comparing service processes; its initial overbroad assertion was corrected.
  The measurement's within-run process guard remained unchanged and passed.
- Temporary VM files were removed after successful retrieval and verification.

## Evidence and follow-up

[Aggregate JSON](2026-10-01-vm-project-identity-summary.json),
[serial comparison CSV](2026-10-01-vm-project-identity.csv),
[local implementation/results](2026-10-01-project-identity.md).
Private raw evidence: `/Users/rosenth/.codex/oldap-vm-identity-20261001/`.
Reproduce using the existing Docker-host read harness and saved complete-batch
catalog with `--seconds 30 --users 1 8 16 1`; see the performance README.

Retain four workers/two threads. This modest, useful optimization is accepted
on the deployed VM. Larger-data and sustained mixed-user measurements remain
separate work; no further Python rewrite is implied by these measurements.
