# OLDAP API 1.2.2 — archive placement status

Fix placement summaries on Jena: use RDF 1.2 grants and selected-schema class
inheritance, bind entry/direct-media branch inputs locally, deduplicate candidates
and join placements as a set. Preserve read thresholds, asserted memberships and
protection for placements in unreadable archive units. Existing GraphDB permission
syntax remains supported. No ontology or data migration is needed.

Local HTTP verification matches ordinary linked-media search totals: 255/255
media/free in 0.20s, 1/1 in 0.19s and 7/6 in 0.17s. The initial correlated query
took 54.41s for the 255-medium album. These are single local samples, not load-test
percentiles. Ten contract/isolated real-Jena tests cover inherited types, empty,
entry/direct/mixed selections, hidden destinations, restricted/orphaned grants and
an album with 255 media and duplicate permission reifiers.

Release scope: API 1.2.2 Docker images for AMD64 and ARM64, with unchanged oldaplib
1.2.1 and retained third-party constraints. Publish source and the version tag;
no PyPI publication is requested. Deploy the immutable image to home API/identity
through the existing routine updater. Production and frontends are outside scope.
Publication/deployment evidence and rollback references are recorded below.

## Verified publication and home activation

Final tag v1.2.2 and source commit 7066cbb are pushed. The existing version workflow
created an intermediate v1.2.2rc1 Git tag before finalization; Docker publication
uses only final v1.2.2 tags. AMD64/ARM64 images passed 108 installed regression
tests each, real-Jena placement acceptance from installed image code and packaged
Jena transaction, replacement and isolation checks. The final multiarch image is
`lrosenth/oldap-api@sha256:aff1d3dd2a133290358ff3951c1a976a98ef82df9df86fe2d2d7927f3d5bcdba`;
latest is unchanged. No PyPI package was published.

Home runs API 1.2.2 with library 1.2.1. Only API and identity containers changed;
six other containers retained their IDs. Public/authenticated checks each cover
20 direct media and three linked entries, comparing totals to ordinary searches.
The 255-medium album status took 0.145s public / 0.157s authenticated inside the
running container. Health and archive HTTPS pass; the final plan is unchanged.
No live content or placement writes were performed. Production was not deployed.

Rollback: select `oldap-setup/releases/home-1.2.1.json` through the same routine
updater. Private configuration backup: `/opt/oldap/compose/routine-update-20261115T223704559931Z`.
The home-specific current release selection is `releases/home-1.2.2.json` in
oldap-setup. Exact receipts: [release-1.2.2-results.json](release-1.2.2-results.json).
