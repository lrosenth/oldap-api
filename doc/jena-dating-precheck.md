# Model-driven dating eligibility before search hydration

## Change

Structured search responses previously constructed ResourceInstanceFactory even
when only title/literal properties were requested. That deserialized project and
shared models and prepared two list namespaces before discovering no Dating field.

`_search_may_include_dating` in `oldap_api/views/instance_views.py` now performs one
small ASK over project/shared/base SHACL graphs. It checks requested property IRIs
against `sh:class oldap:Dating`, matching `sh:path` or modeled inverse `oldap:field`.
This is a conservative eligibility check, not validation or a reasoner: matching
any declaration keeps the original path. It intentionally ignores the owning
class so inherited and reusable properties cannot be missed by a duplicate class
hierarchy implementation. A false positive only preserves the former work.

If no field matches, return without building the factory. Otherwise the existing
resolved-property selection, 100-row batching, read-permission checks and removal
of unreadable references run unchanged. No special field names, data-result cache,
authorization cache, public signature or response format changes. New model fields
and removed declarations are observed on the next lookup. Count-only and empty
responses retain their early exits. Request identifiers use validated RDF terms.

The small ASK also succeeds directly against the unchanged local GraphDB source
(title false, Fasnacht dating true); no old GraphDB API checkout was modified or
deployed. This is query compatibility evidence, not a full GraphDB API regression.

## Validation and performance

The owned real-export fixture runs the same six cases with 8 GiB Java heap.
`profile_backend_search.py --compare-dating-precheck` alternates baseline/optimized
in ABBA order twice after warm-up, four timed samples per case/plan. Baseline
bypasses only the new eligibility check, preserving the former factory path.
All 60 full API responses agree, including dates, order, scores and metadata;
23 fixture checks also pass. Source export hash unchanged; owned services stopped.

| Case | Before median (ms) | After median (ms) | Backend calls before → after |
|---|---:|---:|---:|
| metadata | 157 | 119 | 4 → 3 |
| count | 88 | 85 | 2 → 2 |
| dating | 361 | 357 | 6 → 7 |
| dating_count | 144 | 145 | 2 → 2 |
| fulltext | 162 | 118 | 5 → 4 |
| fulltext_count | 88 | 86 | 3 → 3 |

Metadata pages improve ~24%, fulltext pages ~27%. Real dating pages remain broadly
unchanged in this small run; they now pay one extra ASK, so do not interpret the
minor measured improvement as a dating speedup. Count paths are unchanged; their
small differences are noise. These are serial local measurements, not concurrent
capacity or a new GraphDB comparison.

Ten focused offline tests pass. They cover live project/shared/base declarations,
inherited declarations, reusable and inverse fields, newly added/removed fields,
factory avoidance, unchanged metadata/scores, 100+1 hydration batching and unreadable
date omission. Native Jena also verifies newly inserted and removed declarations
and an inverse modeled field; real date pages preserve full baseline responses.
RDFLib emits existing dependency deprecation warnings during the new RDF tests.
Compilation and diff checks pass.

Use the preceding profiler command with `--compare-dating-precheck` and a new
private output directory. Raw query/profile files stay private; aggregate evidence
is [retained here](jena-dating-precheck-results.json). The next optimization remains
actual model/date hydration and its queries, not additional permission caching.
