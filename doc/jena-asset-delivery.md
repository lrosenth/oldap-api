# Jena PDF and original-file delivery rehearsal

This opt-in rehearsal extends the owned real-export browser fixture with the
existing Caddy/mediahelper delivery path. No running service is changed. The
installed `lrosenth/oldap-mediahelper:normalization-local-20261010` and `caddy:2.8`
images run in a new Docker network. Only Caddy has a new loopback host port. Its installed binary requires
`NET_BIND_SERVICE` to execute; the fixture drops other capabilities and retains
`no-new-privileges`. The first run exposed this startup requirement and cleaned up
its owned services before the corrected retry.
Copies of the 1948 BMG minutes PDF (original and derivative) and the 1912 lantern
JPEG original are mounted read-only. Source hashes are verified again on exit.

## Reproduction

Add `--asset-service-root <oldap-mediaserver-checkout>` to the documented
[image browser command](jena-media-browser.md), retaining `--media-root` and
`--browser-preview`. The repository's Caddyfile is copied unchanged except for
its IIIF upstream, which targets the owned SIPI port. The mediahelper receives
only owned API keys and an API origin reachable from Docker Desktop through
`host.docker.internal`. This is a macOS Docker Desktop rehearsal, not a portable
production deployment recipe.

Use `browser-ready.json` for the frontend API/media origins. The actual PDF IRI
is in `asset-results.json`. The public identity cannot read this internal PDF;
use fixture actor / owned-fixture-password for the authorized browser check.
The public lantern JPEG original is checked with the public identity's capability.
`browser-stop` or the 20-minute deadline removes owned containers/network and
stops the owned API, Jena and Redis. Stop the separate Vite preview as well.

## Checks and interpretation

- Byte-for-byte SHA-256 equality of PDF derivative, PDF original and JPEG original.
- Content type, attachment/inline disposition, HEAD length, range response and CORS.
- Internal filesystem response headers do not reach the client.
- Public API cannot issue a capability for the internal PDF.
- Missing, invalid, expired and wrong-asset tokens cannot retrieve the internal PDF.
- Existing mediahelper policy differences are recorded separately, not counted as
  security acceptance: anonymous fallback on invalid supplied tokens, and handling
  of an independently signed zero-permission capability.

The zero-permission diagnostic uses only the fresh owned fixture signing key;
clients cannot modify a real token without invalidating its signature. It checks
policy enforcement at the delivery boundary, not an unsigned token forgery.

This does not establish production readiness, upload behavior, complete binary
migration, automatic expiry renewal, or equivalent authorization semantics between
SIPI and the mediahelper. Already-issued valid capabilities keep their lifetime.

## Findings from the real run (2026-10-31)

The eight grouped transport/access checks pass. Both policy diagnostics return
HTTP 200: a validly signed zero-permission token serves the internal PDF, and an
invalid token serves the public JPEG through anonymous fallback. The internal PDF
remains HTTP 404 for missing/invalid/expired/wrong-asset credentials. Therefore
transport compatibility passes, but delivery-policy hardening remains an explicit
cutover blocker. Align fail-closed supplied-token handling with SIPI and define
and enforce the minimum permission for complete originals/document delivery.
Do not interpret this rehearsal as approval of the existing policy.

Browser testing exposed a separate existing archive-page bug: non-IIIF URLs
omitted the already-issued media capability. Public files masked the problem;
the internal PDF failed to load. The archive mapper now uses the established URL
helpers for local full files and thumbnail derivatives, retaining their token.
External provider URLs are unchanged. API/library public signatures are unchanged.
The frontend production build passes. Targeted ESLint still reports the same
pre-existing `svelte/prefer-svelte-reactivity` Map error at line 588; checked against
the pre-change text to distinguish it from this fix.

The corrected browser displays all four pages and successfully navigates from
page 1 to page 2. All 23 real-export API checks and ten image checks still pass;
two focused offline tests pass. Source hashes match after cleanup and all owned
services are stopped. See [aggregate evidence](jena-asset-delivery-results.json).


## Authorization correction verified (2026-10-31)

The previously recorded policy findings are corrected in mediahelper repository
source. Invalid/expired/empty/duplicate supplied tokens and wrong/missing asset
identity return 403 without anonymous fallback. Integer permissions 1..6 are
required for both capabilities and public lookup results; the existing SIPI
minimum DATA_RESTRICTED=1 is retained, not raised to a new original-download tier.
A genuinely tokenless public request still works. Public API routes/signatures
and successful delivery shapes are unchanged; malformed formerly accepted
capabilities are now intentionally rejected.

The updated owned rehearsal mounts the mediahelper source read-only into the
installed runtime image. Nine grouped asset checks, 23 API checks and ten image
checks pass. Both formerly successful negative diagnostics now return 403;
PDF/original bytes, range responses and CORS still pass. The mediahelper suite
passes 374 tests plus four subtests, with 20 environment-dependent skips.
Source hashes remain unchanged after cleanup; all owned services are stopped.
See [correction evidence](jena-asset-authorization-results.json) and
[delivery policy](../../../OLDAP/oldap-mediaserver/docs/asset-authorization.md).

The source defect is fixed, but a rebuilt/versioned mediahelper release and
explicit deployment remain required before the production cutover gate closes.
The previous browser rendering check remains valid historical evidence; this
correction was verified through real HTTP delivery rather than repeating the UI.
