# Archive and mobile lifecycle merge verification

The integration combines local archive commit `2f7af33` with mobile lifecycle
commit `9f76807`. It requires the matching oldaplib checkout integrating `689faf5`
(0.7.17 resource hooks) with the archive transaction boundary. No package was
published, dependency lock refreshed or service activated by this merge.

## Preserved behavior

- Generic update keeps the coordinated fresh read and preparation-note check
  before payload mutation/class validation. Archived note writes and clears are
  rejected with the existing 409 `{message}` response before any outbox work.
- The mobile-origin move/archive/delete callback adds lifecycle facts within the
  same owning transaction. The merged library runs it after archive reference
  retention and audit. A callback failure rolls back all these writes; joined
  operations never commit independently or recover a poisoned outer transaction.
- Mobile receipt resource identifiers remain immutable `xsd:anyURI` metadata.
  The narrowly scoped old-receipt normalizer runs only after authorized deletion
  encountered an in-use conflict. Actual incoming application/private references
  continue to block deletion. Coordination, archive conflict and mobile receipt
  failure mappings all remain present.
- Existing archive APIs and both new internal worker lifecycle routes coexist.
  No existing path definition was replaced. Purpose-specific service tokens and
  their separation from commit/auth capabilities remain as implemented upstream.
- Existing Capture request/result shapes are unchanged. No CaptureApp file was
  modified. Native AS-T12 acceptance and target rollout checks remain open.

## Verification (2026-09-08)

- 236 focused API tests and 22 subtests pass: mobile commit/lifecycle/repository,
  staging routes, archive HTTP boundaries and all export suites.
- Added a regression proving post-archive note rejection precedes payload changes
  and mobile hooks, including clear operations. Updated the incoming route test
  double with the property model required by the retained generic validator.
- Actual isolated GraphDB/Redis lifecycle probe passes: transfer/rollback,
  references, concurrent operations, stale writes, notes and permanent receipts.
- Actual isolated reviewed-adoption probe passes, including read-only preflight,
  atomic rollback, exact retries, second delivery, revocation and concurrent apply.
- OpenAPI: no duplicate mapping keys, all 84 paths from both parents retained,
  preserved archive schemas, added worker schemas/security, all 812 local refs valid.
- Actual Capture note/parser source bundled in memory: ten status/payload cases,
  three bounded refresh sequences and unchanged commit/duplicate parsers pass.
- Prior matching-library verification: 76 focused tests plus all 63 real
  ObjectFactory tests, including the coworker's new callback regressions.

Only owned disposable test repositories/Redis were written. Application data,
production services and native client source were not changed. Existing warnings
about unrelated regex escapes in datamodelling views are not merge regressions.
The local source now differs from the historical AS-08 snapshot; the checks above
are merge verification, not a replacement for its outstanding native/target sign-off.
