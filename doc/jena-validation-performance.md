# Trusted RDF reads and datatype validation performance

## Decision

Database RDF values are validated on write. Read-side reconstruction uses the
existing `validate=False` / `fromRdf` paths. Necessary lexical decoding remains;
new external inputs, tokens and independent resource authorization still require
validation. No new public trust flag or signature change is introduced.

The common SELECT reader already uses `fromRdf`; CONSTRUCT now explicitly passes
`validate=False`. `Xsd_gMonthDay` previously ignored its flag for XML Schema
validation and now honors it. Date search expansion keeps database class names
as typed QNames to avoid revalidating them as new factory string inputs.
This is a focused read-path audit, not proof that every repository call site has
been audited. Parsing/type invariants may still reject malformed values.

Remaining input validation previously compiled the same XML Schema on every
call. A bounded cache now retains only the finite datatype schemas; each call
checks its own value and QName namespace with a fresh validation context.
No data, validation result or authorization result is cached. The installed
xmlschema 4.3.2 implementation was inspected for per-call validation contexts;
200 mixed parallel validation cases also pass. Cold concurrent compilation can
occur more than once; correctness does not depend on single initialization.

## Same-target API evidence

Fresh real Fasnacht target, Jena 8 GiB, warm sequential ABBA with four timed
samples per case/plan. All 60 complete responses match; source fingerprint is
unchanged. Both arms use the final trusted-read changes and original SPARQL;
the isolated variable is schema compilation reuse. Values are milliseconds.

| Search | Previous schema compilation | Reused schema | Reduction |
|---|---:|---:|---:|
| Metadata, 100 rows | 111 | 83 | 25% |
| Count | 82 | 60 | 26% |
| Dating, 100 rows | 367 | 278 | 24% |
| Dating count | 135 | 106 | 21% |
| Fulltext, 100 rows | 112 | 58 | 48% |
| Fulltext count | 87 | 39 | 55% |

These are local serial observations, not concurrent capacity or a new GraphDB
comparison. Backend-call counts remain unchanged. The gain includes input/token
processing and must not be described entirely as faster RDF date conversion.
[Aggregate evidence](jena-validation-performance-results.json).

## Rejected query experiments

A count-only correlated EXISTS plan reduced small-source plain/dated HTTP counts
84→64 / 136→115 ms and preserved all 60 responses. On a closed copied fixture
with 12,000 synthetic records it regressed: final warmed plain counts about
154→171 ms and dated counts 887→1559 ms. Result hashes matched in every sample.
It was fully reverted; no dataset-size heuristic was introduced.

Separating date summary CONSTRUCT OPTIONALs into UNION branches reduced Python
RDF decoding but increased Jena dispatch. Same-target dated HTTP median changed
340→357 ms (60 complete responses still matched). It was fully reverted too.
The objectfactory source is byte-identical to the snapshot before these two
experiments. Preserve these findings to avoid repeating small-fixture-only wins.

## Validation and cutover

41 focused library tests and six API date serialization tests pass, including
trusted SELECT/CONSTRUCT decoding, invalid new inputs, parallel validators,
permissions and class/subproperty semantics. The legacy datatype integration
suite could not run: its configured GraphDB `oldap-test` repository is absent
(44 setup errors, not assertion failures). Do not change that external fixture
as part of this work. Native Jena acceptance passes 208 checks, including relationship growth and
current role removal; owned services were stopped.

The shared library changes also apply to GraphDB-backed consumers when ported,
but the original GraphDB checkout and running deployment were not modified.
No public API, harvester or tools signature migration is required. Existing
production import/write validation remains a prerequisite of trusted reads.

Private reproducibility artifacts: `count-plans-01`, `count-growth-plans-01`,
`count-exists-api-01`, `dating-union-api-01`, `trusted-rdf-api-01` under the local
OLDAP-Jena probes directory. The profiler accepts trusted snapshot controls via
`--baseline-count-profile`, `--baseline-summary-builder`, `--baseline-validator`.
Private RDF, request payloads and credentials are not copied into this report.
