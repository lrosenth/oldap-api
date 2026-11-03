# Bounded entailment: API acceptance and performance

The library now supports scoped class ancestry/equivalence and inverse property
reads without enabling an OWL reasoner. Implementation and limits are explained
in [the library guide](../../oldaplib/docs/migration/jena-bounded-entailment.md).
API routes and public library signatures remain unchanged.

## Acceptance

The actual Chama migration is repeated from unchanged GraphDB source exports into
owned Jena/TDB2 and a normal API with its own Redis. The final comparison includes:

- The original 112 project/model/resource reads as administrator and anonymous.
- Eight additional source/target comparisons: 54-resource summaries, superclass
  search, equivalent-class search and inverse-property search, for both actors.
- Seven native synthetic checks: both inverse axiom directions, equivalent-class
  cycles and cross-schema ancestry, foreign graph exclusion, no derived ACL/type/
  provenance, summary parity/denial, transaction-local deregistration and rollback.

All 120 source/target comparisons match. Source project/schema/admin export bytes
and the original API baseline remain stable when reread. Comparisons normalize
array order; they do not establish UI ordering or a coordinated source snapshot.
The isolated target is extended for scale tests **after** behavioral comparison.

The previous 154 real API integration checks and 126 native model/search checks
also pass, including archive operations, writes/rollback, fulltext and permissions.
41 focused offline tests pass. RDFLib emits upstream deprecation warnings in the
in-memory query tests; no failed checks remain in these runs.

## Migration metadata and API compatibility

The source namespace registry is exported privately. Only missing prefixes used
in observed source API responses are installed in the target API's context. This
preserves compact output such as `foaf:Person` without adding ontology graphs to
entailment scope. No FOAF- or Chama-specific rule is added to the library.
A production deployment needs durable prefix provisioning at startup; the rehearsal
currently installs it in its owned process and retains the private namespace file.

Search filtering and class matching use the common rules. Existing search
`includeProperties` stays asserted-only, as on GraphDB, even when an inverse-only
filter matches. Single-resource and summary reads include the derived values.
The search projection distinction was explicitly checked against the source API.

## Measurement method

`tools/migration/benchmark_project_reads.py` performs serial real HTTP requests
on the owned target. Each case has three cold-object-cache samples and seven warm
samples, with raw samples retained. The benchmark flushes only its own Redis cache.
Cold means an empty OLDAP object cache, **not** cold JVM, OS or TDB storage caches.
Cases are a person resource, the 54-resource summary batch, and a `schema:Thing`
class search with normal paging. No other migration probe ran during final timing.

The baseline is the previous incomplete read implementation, captured before code
changes. The new class search legitimately finds additional resources through
external vocabularies, so its before/after time is not an identical-result cost
comparison. Resource/summary requests keep the same root selections but now return
the missing derived information. These are local diagnostics, not load/SLA claims.

An additional owned fixture creates 1,000 synthetic people using the existing
modeled class and role/grant pattern. This tests sensitivity to instance count;
it does not replace a larger real project or concurrent production benchmark.
The same HTTP cases are repeated after population. The summary still selects the
original 54 identities; search remains paged, rather than returning all people.

The first scaled run exposed repeated class-path evaluation per instance. Class
searches now select and test distinct instantiated classes before joining
authorized resource instances. Dynamic
archive-policy class variables retain the correlated test because SPARQL subqueries
cannot inherit their outer binding. Both forms use the same class path and scope.

## Measured medians (milliseconds)

| Case | Previous cold | New cold | Previous warm | New warm | New warm, +1,000 people |
| --- | ---: | ---: | ---: | ---: | ---: |
| One person | 1,725 | 1,763 | 141 | 175 | 174 |
| 54-resource summaries | 1,948 | 1,965 | 311 | 414 | 383 |
| `schema:Thing` search | 98 | 129 | 62 | 96 | 1,186 |

Warm single reads add about 35 ms (+25%); summaries add about 103 ms (+33%).
Cold-object-cache changes in this small run are much smaller in percentage terms.
These numbers do not justify a promise of negligible overhead. Single/batch reads
remain stable in the synthetic growth case; broad class search is still around
1.2 seconds at that size and needs further realistic load acceptance.

To distinguish new rule cost from existing search cost, a paired test queries
`chama:Person` on the grown dataset. It alternates seven measured requests per
mode after a discarded warmup pair, using the same owned API/Jena and requiring
identical 100-result pages. A test-only control restores previous schema selection
and superclass-filter rules in the current code. Medians: **900 ms with bounded
entailment versus 1,720 ms with the previous-rules control**. This supports the
class-selection optimization; it is not a historical production-release benchmark.
No test override remains enabled after the control request.

The [sanitized evidence](jena-bounded-entailment-results.json) retains raw samples,
counts, checks and measurement caveats. Private run: `j28-after-07`; baseline:
`j28-before`. Earlier experiments identified expensive repeated paths and ARQ join
placement; their timings are not substituted for the final measurements.

## Reproduction and evidence

Run `tools/migration/probe_graphdb_project.py` as documented in the
[original rehearsal](graphdb-project-rehearsal.md), adding:

```sh
--benchmark --scaled-benchmark --entailment-checks
```

The benchmark fixtures deliberately select Chama; another project needs suitable
sample identities and classes. Source access remains read-only apart from ordinary
API login/cache behavior. All target listeners, Redis and Java processes are owned
and stopped. No production configuration, source data, deployment, commit or push
is changed. Private outputs remain outside Git; the sanitized results accompany
this document.

Full OWL semantics, inverse-aware fulltext indexing, production cache/concurrency,
large real exports, general account migration, binaries and cutover recovery remain
outside this acceptance. See the [cutover index](../../oldaplib/docs/migration/graphdb-to-jena-cutover.md).
