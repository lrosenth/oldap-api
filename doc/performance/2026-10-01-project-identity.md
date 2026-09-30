# Project identity projection — 2026-10-01

## Outcome and decision

Property model reconstruction now resolves only the three project identity
values it retains: short name, project IRI and namespace. It no longer copies
labels, provenance and project change tracking for every property when an
operation-local project snapshot is available.

The change saves roughly 9–11 ms for anonymous medium reads in two local rounds
(**13–16%**). The rosenth medium comparison improves **10–19%**. Summary reads
improve **6–13%**, depending on user, batch size and round. This is a modest gain,
not a consistently achieved 15–20% improvement across all operations. Retaining
this small, localized change is proportionate; broader model caching or datatype
copy changes are not justified by this experiment.

## Implementation and ownership

`Project._read_identity()` is internal to model construction. It returns a deep
copy of the identity tuple from the existing connection-bound, operation-local
snapshot. No second cache or lifetime is introduced. On a miss or outside the
scope, normal `Project.read()` supplies the values and propagates its errors.
Successful `ignore_cache=True` reads refresh the same snapshot as before.

`PropertyClass.__init__` uses this projection for project identifiers. Explicitly
supplied Project instances retain their existing constructor behavior. Full
Project reads and ResourceClass objects still receive independent complete
copies, with their original connections, labels, notifiers and change tracking.
No permissions, JSON formats, GraphDB queries or API routes change.

An exploratory direct-state-copy Project prototype was discarded. Its closing
source inventory overlapped preparation of the next prototype, so that run is
excluded from the formal results below. The final Project deepcopy method is
unchanged. All four accepted timing runs have matching start/end source hashes;
the repeated pair also records `propertyclass.py`, newly added to the harness
inventory. Candidate files are unchanged throughout accepted measurements.

## Local sequential reads

Source-pinned oldaplib 0.7.24 baseline versus modified 0.7.24 checkout; same API,
Python 3.13 interpreter, local GraphDB and Redis. First round: 20 uninstrumented
samples per case/user, plus separate instrumented samples and profiles. Repeat:
30 uninstrumented samples for each interactive case/user. Both rounds run before
then after; no cache flush. Times are median Flask test-client request latencies,
not timings of the separately installed native API.

| User | Operation | First before → after | Reduction | Repeat before → after | Reduction |
|---|---|---:|---:|---:|---:|
| UnknownUser | Medium | 65.9 → 55.4 ms | 16.0% | 64.7 → 56.0 ms | 13.4% |
| UnknownUser | 25 summaries | 79.2 → 69.0 ms | 12.9% | 78.9 → 69.5 ms | 11.9% |
| UnknownUser | 100 summaries | 112.2 → 101.6 ms | 9.5% | 110.0 → 101.9 ms | 7.4% |
| rosenth | Medium | 88.4 → 72.1 ms | 18.5% | 81.0 → 73.0 ms | 9.9% |
| rosenth | 25 summaries | 104.4 → 92.2 ms | 11.7% | 101.0 → 93.9 ms | 7.0% |
| rosenth | 100 summaries | 158.9 → 143.6 ms | 9.6% | 157.1 → 147.8 ms | 6.0% |

Fresh Fasnacht model retrieval, measured only in the first round, changes from
210.2 to 205.4 ms anonymously and 234.7 to 218.4 ms for rosenth. These small,
unrepeated differences should not be treated as established gains.

Anonymous medium CPU time falls from 57.6 to 47.2 ms initially and 55.9 to
47.7 ms in the repeat. The separate profile shows **524 → 181** full Project
copies and 343 identity projections. Total profiled calls fall from 1,043,441
to 788,373. Profiler elapsed times include instrumentation overhead and are not
latency estimates. Instrumented medium reads retain **3 GraphDB queries and
42 Redis reads**. The benefit is reduced Python work, not fewer database calls.

## Verification and boundaries

- **1,000 accepted timed requests**, all HTTP 200.
- All **34** before/after normalized content hashes match: 17 read cases for
  UnknownUser and rosenth. Each version also matches the native API's normalized
  content. Normalization uses the existing unordered-array and media-capability
  rules; it is not byte-for-byte JSON equality.
- **75 library, 14 API and 19 read-tool offline checks** pass. New tests cover
  independent identity wrappers, alias lookup without full copying, scope and
  connection boundaries, refreshed snapshots, thread/failure isolation, and
  real PropertyClass construction. Existing full-copy/notifier tests remain.
- Every accepted run and both complete-catalog checks retain the explicit
  named-graph fingerprint: **52,490 bindings**, SHA-256
  `22a0fec5fe229ce12513d0c6e4e21c5d38f035df2cbb0365958e9085d7a83b26`.
- The measurement transport blocks graph mutations, cache deletion and cache
  clearing. Normal cache population is allowed. Destructive integration suites
  were not run.

No package installation, native-service restart, version bump, deployment or VM
change occurred. These short sequential laptop comparisons do not establish
production latency, concurrency gains or maximum capacity. The next operational
step is a normal library release and consumer update, followed by the existing
read-only VM comparison with unchanged four-worker/two-thread settings.

Machine-readable evidence: [summary JSON](2026-10-01-project-identity-summary.json)
and [comparison CSV](2026-10-01-project-identity.csv). Private raw evidence and
source snapshots: `/Users/rosenth/.codex/oldap-model-copy-20261001/`.

Reproduce each timing pair using `tools/read_performance.py`, source selection
through `PYTHONPATH`, the same saved case catalog, `--mode inprocess` and the
resource_media/summaries_25/summaries_100 cases. Use separate processes and output
directories; capture instrumented spans separately from uninstrumented latency.
Run `--verify-only` for the full catalog on both source versions. Do not compare
the candidate to the native installed library version as a substitute baseline.
