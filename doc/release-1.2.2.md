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
Publication/deployment evidence and rollback references follow acceptance.
