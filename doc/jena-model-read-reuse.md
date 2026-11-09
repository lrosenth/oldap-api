# Operation-local superclass reconstruction

## Profile-driven choice

After datatype-schema reuse, a fresh six-case profile passes all 42 requests.
[Sanitized profile](jena-post-validation-profile-results.json).
The dated 100-row search has a 294 ms median: about 182 ms native dispatch,
8 ms backend authentication and 92 ms other API work. JSON-LD decoding accounts
for about 29 ms and CONSTRUCT processing for 16 ms; these are nested spans, not
additional independent costs.

The separately profiled dated request reconstructs 342 PropertyClass objects,
59 ResourceClass objects and performs 37 recursive ResourceClass.read calls.
DataModel.read consumes 141 ms with cProfile enabled. The 101 per-result
resolved_properties/createObjectInstance calls cost only about 1 ms each in
aggregate, so optimizing that loop was not justified. Profiled durations include
instrumentation overhead and must not be compared directly with HTTP medians.

## Change

During one synchronous ResourceInstanceFactory initialization / DataModel.read,
reuse private snapshots of Redis-loaded ResourceClass models. The same project
and class on the same connection are reconstructed once, then independently
copied. This follows the existing project-read scope pattern; it is not a
process-wide model cache. Each copy retains the current connection and rewires
its model/property notifications using the existing deepcopy implementation.

The scope is reset after normal completion and exceptions. Other connections
and threads cannot reuse it. Model loads inside transactions and forced model
reloads bypass it, including positional ignore_cache arguments. Standalone
ResourceClass.read remains unchanged outside a scope; explicit ignore_cache
still bypasses snapshot reads. Only successful Redis hits are retained, not
missing classes, authorization decisions or resource query results.

No SPARQL, public signatures, serialization shape, calendar conversion or
permission checks change. This also applies to GraphDB consumers if ported;
the original GraphDB checkout and running services were not changed.

## Same-target comparisons

Each run uses a fresh real Fasnacht target with Jena 8 GiB, warm sequential ABBA,
four timed samples per case/plan, and complete response equality. The test-only
`--baseline-resource-reader` option loads the previous read method from a
trusted local snapshot without replacing the class/serializer registry.

| Dated 100-row page | Previous reader | Scoped reuse | Reduction |
|---|---:|---:|---:|
| Run 1 | 322 ms | 281 ms | 13.0% |
| Run 2 | 300 ms | 271 ms | 9.7% |

All 120 responses match. Other cases remain broadly unchanged and all backend
call counts stay unchanged. This is a modest, repeatable local benefit, not a
new 25–50% gain or a concurrency/production-capacity claim. The second run had
no overlapping test workload. [Aggregate results](jena-model-read-reuse-results.json).

32 focused library tests and six API tests pass. New tests exercise independently
mutable models/notifications, the original connection, fresh subsequent loads,
nested connections, cleanup on errors, forced reloads and overlapping threads.
The native Jena probe passes 208 checks including 1000-child growth, duplicate
values/grants, live role removal and current fulltext permissions. Source
fingerprints are unchanged; owned services were stopped.

## Follow-up

JSON-LD graph decoding and native query dispatch now deserve separate study.
Changing RDF transport formats could avoid generic JSON-LD work, but requires
protocol negotiation and compatibility tests; no transport change is made here.
Concurrent performance and a new GraphDB comparison remain separate steps.
Private artifacts: post-validation-profile-01, model-scope-api-01/02 and
model-scope-native-01 under the local OLDAP-Jena probes directory.
