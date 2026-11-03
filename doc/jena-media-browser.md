# Signed image delivery on the owned Jena browser target

The optional `--media-root <source-media-root>` argument extends the real-export
`--browser-preview` rehearsal with a disposable SIPI container. It copies only
the 1912 lantern's `derived/master.tif` into the private output directory. The
source tree is never mounted into the container. Source SHA-256 is checked before
and after the rehearsal. The copy is mounted read-only; Docker binds only a new
loopback port. The existing media server, its cache and production keys are unused.

The locally installed `lrosenth/sipi-2:0.1.3` image must already be available;
`--pull=never` prevents an implicit image download. Its normal OLDAP Lua policy
receives the owned API's freshly generated media key through the environment,
never through a command-line value or a committed configuration file. Only signed
capability access is enabled. Anonymous SIPI-to-API fallback is a separate gate.

## Acceptance on 2026-10-31

All 23 real-export API checks, ten signed-media checks and two focused offline
instance-read tests pass. The existing frontend displays the 1912 lantern image
as the public identity; zoom and reset work. The source derivative hash is
unchanged after cleanup. All owned services were stopped. See
[aggregate evidence](jena-media-browser-results.json). Public API signatures and
frontend/runtime implementation remain unchanged.

## Reproduction

Use the command in [browser rehearsal](jena-browser-rehearsal.md), adding
`--media-root <source-media-root>`. After `browser-ready.json` appears, start the
frontend with its `PUBLIC_API_URL`/`SERVER_API_URL` set to `api_url` and
`PUBLIC_MEDIASERVER_URL` set to `media_url`. Use the same isolated media origin
for `PUBLIC_UPLOAD_URL` (uploads are not exercised or served by this fixture).
Open the lantern media detail identified in `media-results.json`.

The helper automatically checks API capability issuance, actual JPEG delivery,
CORS/HEAD, revoked membership blocking new issuance, restoration, and denial of
absent/invalid/expired/wrong-asset/zero-permission tokens. It restores the one
removed membership before browser use, including on a failed assertion. Imported
permission annotations are retained throughout. The full real-export comparison
runs before these temporary fixture changes.

Create `browser-stop` to finish; the existing 20-minute preview deadline also
closes the owned services. The SIPI container is removed in `finally`. Private
outputs contain the image, source hash and metadata, but the aggregate report
contains no tokens. Keep the private output outside Git.

## Permission semantics and limits

A media capability is a bounded authorization snapshot. Revocation prevents new
capabilities; an existing token remains usable until expiry. The isolated SIPI
instance has no persistent encoded-image cache. This does not establish production
cache behavior or immediate revocation of already-issued capabilities.

This step covers one signed TIFF-to-JPEG image and browser zoom. PDF and original downloads are subsequently exercised in the
[asset rehearsal](jena-asset-delivery.md), which exposes policy differences.
Other assets, uploads, anonymous fallback for SIPI, automatic token-expiry renewal,
production load and a complete binary migration remain separate acceptance gates.
