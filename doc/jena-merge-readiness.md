# API merge preparation — 2026-11-03

**Merge gate remains open: the normal-speed full integration probe fails.**

Local checkpoint on `migration/jena`, paired with library commit `827bc56`.
This is not a final 1.0 release or deployment approval. The coordinated sequence
is in [setup's merge plan](../../oldap-setup/docs/jena-1.0-merge-plan.md).

## Scope and corrections

Retain the explicit GraphDB/Jena backend boundary, database-free private identity
verification, project fulltext administration, service-token connections for
export/import/mobile workers, RDF 1.2 conflict responses, inverse model fields,
dating query optimization and private-safe import diagnostics. Migration probes
and historical performance/acceptance evidence belong with the implementation.

Existing route declarations in modified modules are unchanged. New fulltext
routes and the private identity route are additive. Runtime argument lists stay
unchanged; connection type annotations use IConnection. New `inversePath` model
metadata and explicit 409 outcomes are documented changes, not a claim of
identical responses for every legacy request. The Jena health response names Jena
instead of GraphDB; it retains the existing HTTP 200 health-report convention.

Review corrected the following gaps:

- The OpenAPI property schemas now document the implemented `inversePath` field.
- Non-ASCII credentials on the private identity route formerly caused a TypeError
  and HTTP 500. Comparing encoded bytes returns HTTP 401 without decoding the
  supplied access token. A regression reproduces the failure before the fix and
  covers missing, wrong and non-ASCII credentials after it.
- API startup documentation now refers to the selected backend.
- The real API probe now runs its identity verifier in a separate owned process,
  matching the home deployment. The child receives only synthetic verification
  settings and is terminated on success or failure.

## Verification and limits

- 61 focused tests and 13 subtests pass with socket connect/connect_ex blocked:
  backend/worker authentication, fulltext administration, dating, import audit and
  views, export views, instance reads/search and archive structure routes.
  No shared GraphDB or Redis is used by this test selection.
- OpenAPI 3.1 validation passes. Candidate Python parses and evidence JSON loads;
  a private-key/JWT/token-pattern scan found no matches. Existing regex escape,
  RDFLib and Poetry metadata deprecation warnings remain.
- Poetry check, focused Black checks for the identity implementation/regression,
  and whitespace checks pass. No wholesale reformat of the migration is performed.
- A local wheel builds with the new modules and export profile data. Extracted
  final-wheel imports, backend selection and malformed-identity rejection pass
  outside the checkout, using existing dependency installations.
- Real API acceptance uses a separately owned loopback Jena process, synthetic
  identities/data and suppressed shared Redis cache access. The real Tools CLI
  participates in model/fulltext import and dump checks. Retain its sanitized
  result in `jena-merge-api-results.json`; private fixtures and logs stay outside
  Git. This is not home.org or production acceptance.

The initial full run preceded the non-ASCII-header correction; subsequent
runs, including the independent verifier, use the corrected source. Malformed headers are also
covered by the network-blocked regression and extracted-wheel check. Existing broad/destructive GraphDB fixtures
were not run. Installed production images have not changed.

## Remaining 1.0 gates

The wheel still embeds the editable sibling library's file dependency. It is a
local inspection artifact, not independently distributable release evidence.
Replace this dependency in the coordinated 1.0 packaging step and retest clean
installed artifacts, without editable checkouts. Version remains 0.2.37 and must
not be republished. The OpenAPI top-level version is historically 0.1.0; synchronize
it with runtime/package/bump metadata during the 1.0 step.

Review current consumers, final candidate images, home workflow/concurrency and
backup/restore acceptance before merge/deployment. The old full probe returned COORDINATION_UNAVAILABLE
(503) instead of STALE_REVIEW (409) after retrying an already-applied archive plan.
Normal-speed repeats reproduced it; tracing or running the archive case alone
masked it. Lightweight diagnostics identified the backend refusal as "Identity
verification unavailable" on a model READ. The old probe hosted callbacks inside
the API process, unlike the independently deployed verifier. Its lifecycle now
uses a separate process. The separate-verifier full run also fails with 503 at the same stale-plan
assertion. Process separation is therefore not a proven fix. The 409 assertion
and application transaction semantics remain unchanged. Investigate the verifier
transport/response failure under the normal full request sequence before marking
this branch merge-ready. Do not weaken assertions or add automatic write retries.
The passing traced run is diagnostic evidence, not final integration acceptance. Git main, release tags, remote
branches, Docker Hub and production remain unchanged by this checkpoint.
