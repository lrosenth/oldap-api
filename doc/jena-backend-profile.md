# Jena search latency decomposition

## Scope and method

Follow-up to the [heap experiment](jena-heap-comparison.md). Same six real-data
public searches, 100-row limits, 8 GiB maximum heap, fresh owned API/Redis/Jena.
This profiles Jena, not the live GraphDB process; it does not partition the full
GraphDB-versus-Jena difference by cause.

Runner: `tools/migration/profile_backend_search.py`, with the same CLI as the
comparison runner. The six request bodies now live in the shared `search_cases()`
function, preventing workload drift. Replace the script in the heap command.

Six warm-up requests, five timing repetitions per case (30 requests), then six
separate cProfile requests: 42 successful, full-response-stable requests total.
23 normal fixture checks pass. Source export before/after matches the baseline
SHA-256. No source writes; owned processes stopped. An initial setup was stopped
before measurement to complete timing coverage for fulltext-state/bootstrap routes.

Optional headers on the authenticated private Java probe split token verification
from engine dispatch. Dispatch includes parsing, dataset access, query execution
and result serialization; it is NOT pure query evaluation. No engine changes.
Python HTTP hooks measure the complete backend round trip, and separate wrappers
measure JSON/JSON-LD decoding, ConstructProcessor and dating expansion. The API
span covers Flask dispatch, including response construction. Detailed generated
queries and cProfile files remain in private output, never in committed reports.

Transport residual = backend HTTP minus server authentication and dispatch.
It includes connection setup, scheduling, response transfer and unmeasured servlet
work. API-other = API dispatch minus backend HTTP; it includes Redis/model work,
Python processing and instrumentation, not exclusively CPU time. Dating expansion
overlaps backend calls/decoding and must not be added to those spans. cProfile
roughly doubles some timings and is used only to locate work, not as a benchmark.

## Timing results

Medians in milliseconds; independently calculated medians need not sum exactly.

| Case | HTTP total | Jena dispatch | Token verification | Transport residual | API other | Backend calls |
|---|---:|---:|---:|---:|---:|---:|
| metadata | 171 | 76 | 27 | 5 | 59 | 4 |
| count | 90 | 58 | 12 | 2 | 17 | 2 |
| dating | 378 | 187 | 36 | 8 | 132 | 6 |
| dating_count | 141 | 106 | 12 | 2 | 20 | 2 |
| fulltext | 163 | 48 | 29 | 6 | 72 | 5 |
| fulltext_count | 95 | 34 | 18 | 3 | 37 | 3 |

## Findings and recommended order

1. **Avoid unnecessary dating preparation.** `_expand_search_dating` creates a
   ResourceInstanceFactory before determining whether any requested property is
   Dating-valued. Even name-only metadata/text pages deserialize the project/shared
   models and query both list directories. This whole span costs ~56/~54 ms in
   timing runs. cProfile confirms model reconstruction/deepcopy/property validation.
   First design a small model-driven eligibility check or reuse already available
   model information; preserve inherited and future project fields. Do not hardcode
   schema:name or fasnacht:dating as production exceptions. The measured span is
   an upper bound on possible savings, not a measured optimization speedup.

2. **Reduce avoidable model work during actual date hydration.** Dating expansion
   takes ~217 ms inclusive. JSON-LD decoding accounts for ~29 ms and graph-to-model
   conversion ~18 ms (nested portions). Trace model deserialization and redundant
   namespace/list preparation before changing transport formats. Request-local reuse
   is preferable to new cross-request permission caches. Existing batching and
   fresh per-resource read checks must remain.

3. **Then profile targeted query plans.** Jena dispatch remains substantial: ~76 ms
   for metadata and ~187 ms across the dating queries. The dated root selection and
   summary CONSTRUCT are the large server calls; list/namespace lookups execute in
   ~1 ms but still incur a full authenticated round trip. Their repeated external
   ontology lookup is visible twice in the dated request. Fulltext itself is not
   the dominant whole-request cost in this small fixture.

4. **Treat authentication/transport proportionately.** Token verification costs
   ~6 ms per backend call, ~12–36 ms per API request. Reducing unnecessary calls
   avoids that overhead naturally. Pure transport residual is only ~2–8 ms per
   request, so connection pooling alone is unlikely to close the observed gap.
   Do not bypass token checks or introduce authorization caching from these data.

Only diagnostic tooling changed. No search/query semantics, result fields, public
signatures or deployed services changed. Source/model scope is the existing small
Fasnacht export; concurrent and large-dataset profiles remain separate. Raw aggregate
evidence: [results](jena-backend-profile-results.json). Compilation, native fixture
execution and both repository diff checks pass.
