# Structured dating hydration: repeated namespace resolution

## Finding and implementation

The 437-object Fasnacht list hydrates dates in five authorized summary batches.
Diagnostic cProfile identified repeated `Context.iri2qname` calls as a material
Python cost: roughly 46000 calls within one hydration request. Its instrumented
wall times are not used as performance evidence because profiling itself adds
overhead.

`ConstructProcessor.process` now resolves each distinct URI once within the
current graph, including unknown names. A small local dictionary stores only
namespace resolution results. Fresh QName instances preserve the previous
independent-value behavior; callers can mutate QNames with `+=`. Unknown
predicates remain RDFLib URIRefs, while unknown subject/object values retain
the existing Iri conversion. The dictionary disappears after this call, so
namespace changes on subsequent reads remain visible.

This changes neither SPARQL nor RDF, permission checks, the 100-resource batch
limit, date/calendar/precision/before-link handling, nor API/library signatures.
There is no permission or resource-result cache. The common processor is used
by both backends; the deferred real GraphDB comparison remains open.

## Same-target acceptance

The existing metadata profiler now accepts a trusted pre-edit processor source
snapshot via `--baseline-construct-processor PATH`. In that mode only the Python
processor changes; both modes use the current SPARQL. It records summary-query
and processor timings separately and compares complete HTTP JSON responses.
All 24 responses (six request shapes, twice per mode) agree exactly, including
values, ordering and counts.

For 437 objects, local medians in milliseconds:

| Work | Before | After |
| --- | ---: | ---: |
| CONSTRUCT decoding across five batches | 320 | 75 |
| Complete structured dating hydration | 1004 | 765 |
| Complete object search HTTP request | 1596 | 1365 |

Hydration improves by about 24%, and complete object-search HTTP time by about
15%. Smaller result sets offer less repeated work; their timings are dominated
by fixed costs and local variation. This is not a browser readiness or production
load claim. [Raw samples and check counts](jena-dating-hydration-results.json).

Validation: 188 native model/search checks, 30 fulltext API checks, 23 real-export
API checks, and 49 offline tests pass. New tests cover one resolution per distinct
URI, unknown namespaces, independent mutable QNames and context changes between
graphs. Existing tests cover resource summaries and structured date serialization.
Source export SHA-256 is unchanged; all owned services are stopped.

## Reproduction and next boundaries

Before editing, copy the trusted local `oldaplib/src/helpers/construct_processor.py`
to the private probe directory. Run `tools/migration/profile_archive_metadata.py`
with `--baseline-construct-processor` pointing to that snapshot plus the ordinary
owned-target options documented in [metadata performance](jena-metadata-performance.md).
This option executes the snapshot as Python; use only trusted local source.
Without the option, the prior ACL comparison still works unchanged.

The remaining hydration cost includes fetching/parsing five summary graphs and
model/date conversion. More aggressive changes would touch transport or summary
query structure and need a separate measured justification. No larger cache or
new date-specific API was introduced for this modest, maintainable improvement.
