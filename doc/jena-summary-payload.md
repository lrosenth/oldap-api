# Smaller summary graphs, unchanged JSON-LD transport

## Decision and implementation

Keep the existing JSON-LD protocol and RDFLib decoder. A preliminary local test
on the same 4,799-triple graph, serialized by RDFLib, measured warm decode
medians of 25 ms JSON-LD, 27 ms N-Triples, 35 ms Turtle and 52 ms RDF/XML.
This was exploratory, not a Jena end-to-end transport comparison; it did not
justify introducing format negotiation or a custom decoder.

The important waste was repeated permission-pair blank nodes. The Jena summary
CONSTRUCT previously allocated them after joining requested properties and
ancestor/asserted types. Identical grants consequently produced multiple blank
nodes, all later collapsed by Python into the same public role map.

The RDF 1.2 summary query now materializes those nodes in one bounded subquery
before the outer joins. Its own VALUES clause contains the requested resources;
it does not rely on correlated subquery variables. Each grant gets a distinct
node with exactly one role and permission. Outer access checks, asserted role
membership and grant reifiers remain mandatory. Creator-only access and omitted
unreadable resources retain their previous behavior. Multiple grants/roles and
multiple resources must not merge into one blank node.

The legacy GraphDB branch keeps the original correlated BNODE expression;
its generated query is identical apart from whitespace. Single-resource reads
are unchanged. No public API, library signature, decoder, transport, persisted
RDF, validation rule or inference setting changes.

## Evidence

Real Fasnacht 100-row dated page on owned Jena 8 GiB. Each independent run uses
warm ABBA order with four timed samples per case/plan. Baseline uses the trusted
pre-change summary-builder snapshot; all other current optimizations are active
in both arms.

| Metric | Before | After |
|---|---:|---:|
| API median, run 1 | 306 ms | 231 ms |
| API median, run 2 | 320 ms | 241 ms |
| JSON-LD decode, run 2 | 29.5 ms | 12.6 ms |
| Python CONSTRUCT processing, run 2 | 17.2 ms | 9.7 ms |
| Native dispatch, run 2 | 186 ms | 162 ms |
| Largest backend response | 575,509 bytes | 195,509 bytes |
| Summary RDF graph | 4,799 triples | 1,799 triples |

Dated HTTP latency improves about 24–25% in both runs. Other search cases are
broadly unchanged. All 120 complete API responses agree; source fingerprints
are unchanged. Backend call counts remain seven for this dated page. Decode and
CONSTRUCT times are nested components, not additive with API-other. The gain is
not exclusively decoding: query evaluation, serialization and object allocation
also change. [Sanitized evidence](jena-summary-payload-results.json).

On a closed copied fixture containing 12,000 extra synthetic records, alternating
native measurements of the same bounded 100-resource summary remain favorable:
last-three medians approximately 48→39 ms, with graph sizes 4,799→1,799. This
checks bounded hydration in a larger dataset, not all large-project workloads.

## Regression coverage and limits

209 native Jena checks pass, including 1000-child relationship growth, unreadable,
orphaned and restricted resources, creator-only access, multiple resources with
opposite role/permission pairs, current role removal and fulltext visibility.
A new direct graph assertion requires exactly four distinct permission nodes
for two two-grant resources despite their property/type joins; inspecting only
the public role map would hide the original redundant-node problem.
29 focused decoder/permission/entailment tests pass. Compilation and diff checks
pass. One intermediate probe run stopped on a missing test import; it was fixed
and the entire native suite rerun successfully. Owned services were stopped;
original GraphDB checkout/deployment and source data were untouched.

This is local serial evidence, not production sizing or a concurrent capacity
claim. A fresh GraphDB countercheck remains deferred. Single-resource CONSTRUCT
payloads and concurrent load are possible follow-ups; no speculative decoder
or transport machinery was added.

Private artifacts: summary-role-api-01/02, summary-role-native-03,
count-growth-plans-01/summary-roles.txt and count-plans-01/dates-role-subquery.rq.
The old UNION rewrite remains rejected; this change only moves role binding
construction and preserves the rest of the query plan.
