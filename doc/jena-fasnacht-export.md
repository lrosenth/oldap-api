# Real Fasnacht export rehearsal

## Input format finding

The archived `fasnacht-transfer-2026-10.10.trig.gz` contains 1,985 encoded
`urn:rdf4j:triple:` occurrences. The native converter correctly refuses that
representation. The other inspected local Fasnacht gzip backups also contain
encoded triple IRIs. Do not decode these with text replacement or count such an
export as accepted RDF-star input.

`tools/migration/export_fasnacht_readonly.py` therefore exports the local GraphDB
`oldap` repository with `Accept: application/x-trigstar` and `infer=false`. It
verifies the exact Fasnacht namespace and selects only data/onto/shacl/lists.
It performs no mutation, login, cache operation or account export. All export
files and logs live in new private directories outside Git.

## Rehearsal

Use `probe_api_jena.py --fasnacht-only --fasnacht-export /private/source.trig`
with the existing Java/Jena/output options. The normal production backend is
never selected. The runner uses its own API, identities, dataset and listeners.

`prepare_fasnacht_export.py` preserves the original bytes. If an old tools file
has a leading serialized-account comment header, it retains that exact header
separately and records its digest/count. Accounts are explicitly **not restored**;
account records outside the leading comment preamble are refused. The original
native RDF converter remains unchanged and performs dataset-isomorphism checks.

`ExtractFasnachtData.java` then extracts only the named instance graph from the
converted dataset. The complete converted source, including its old model and
lists, remains retained privately. The target model and taxonomies are provisioned
from the current migration YAML, not overwritten with the legacy source model.

`check_fasnacht_export.py` snapshots the loaded instance graph, runs the reviewed
part preflight and transactionally reverses legacy hasPart statements. It checks:

- Every non-part instance triple is identical, including subject links, archival
  assignments, literals and permission/reifier statements.
- The resulting isPartOf pairs equal precisely the union of original isPartOf
  and reversed hasPart pairs. No hasPart assertions remain; replay is unchanged.
- The ordinary API reverse search matches the readable children for every parent
  in that union. A representative single-resource response uses isPartOf.

The disposable audit actor receives the role identities present in the imported
instance graph, only in the target admin graph. Expected visibility independently
requires asserted membership plus its reified permission at least DATA_VIEW.
No source users or passwords are activated, and no instance grants are modified.
This checks data/API consistency for an audit identity, not real-user login parity.

## Limits and follow-up

This is a current **local** source export, not a production cutover snapshot.
Source export digests are bracketed to detect changes during rehearsal. No claim
is made that legacy omitted/unknown fields render identically across all API
endpoints: non-part preservation is at the RDF level, while API comparison focuses
on part relationships. Fulltext, binary media, account restoration, real-user
permissions, frontend rendering and production cache remain separate gates.

## Result (2026-10-30)

All 23 focused checks pass. The instance graph contains 38,674 triples before
and after migration. Two hasPart assertions are reversed, producing exactly 11
canonical isPartOf pairs. All 38,663 non-part triples are unchanged. One
schema:about link is preserved; there were zero directly stored archiveUnit
assignments, and none were manufactured. API reverse lookups match for all five
parents; one representative single-resource read returns the canonical field.
The audit identity can read 1,548 resources through nine source role identities.

Native conversion preserves 35,829 ordinary quads across the source project
and converts 2,919 permission annotations, with zero orphaned annotations and
zero added memberships; structural round-trip verification passes. Source
exports before/after are byte-identical. Retained [aggregate evidence](jena-fasnacht-export-results.json)
contains no source records, account hashes or instance identifiers.

The observed reverse-search calls took several seconds each in the integration
trace (roughly 7–8 seconds). This is not a controlled performance benchmark;
performance acceptance/optimization remains necessary before production.
