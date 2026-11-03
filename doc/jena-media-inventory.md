# Media lookups and complete inventory hydration on Jena

The existing media lookup functions and HTTP routes keep their signatures,
metadata serialization and token claims. Jena selects a small private query
helper; GraphDB retains its existing queries.

## Query behavior

The helper discovers candidate registered project data graphs, then selects
only that project's ontology plus shared/base schemas for media-class ancestry.
It matches both exact MediaObject types and subclasses such as StagingMediaObject.
The requested identity and caller are bound inside the permission aggregate;
SPARQL subqueries do not inherit outer bindings. RDF 1.2 grants must have the
corresponding asserted role membership in the same data graph and a current
caller role in the admin graph. Orphaned annotations cannot authorize a lookup.

Permission values, including DATA_RESTRICTED, remain available to the existing
media token workflow. This does not introduce a creator or administrator bypass.
The existing result conversion and token signer remain the source of truth.
Multiple visible identities for one lookup are rejected with the existing
inconsistency error (HTTP 400), instead of merging metadata into one capability.

The helper joins an existing transaction. Outside one, candidate discovery and
metadata reads are separate requests; each metadata query rechecks permissions.
It does not promise a cross-project snapshot or revoke already-issued tokens.

## Owned acceptance

`tools/migration/check_media_inventory.py` extends the normal API/Jena probe.
It uses real shared ontology models, a real server policy file, an ordinary
writer and its own socket-only durable Redis instance. Object-cache I/O remains
suppressed, as in previous stages; the user's Redis is untouched.

Model-created staging media exercise ID and IRI lookups, metadata, signed token
claims and restricted permissions. The full inventory endpoint loads model
instances and per-entry capabilities over paginated results. A model-created
catalogue target with an imported reference edge tests read-only reference
capabilities separately. Revocation leaves an orphaned annotation, which must
no longer issue tokens or appear in a fresh inventory. Imported duplicate IDs
and an unrelated ontology graph exercise ambiguity and schema isolation.

## Results

The retained `jena-media-inventory-results.json` records 145 passing integration
checks (132 previous plus 13 media/inventory checks). Targeted offline tests
pass 18 library tests plus 6 subtests and 10 API route tests. All owned processes
closed successfully. The new query helper is documented and tested independently.

## Remaining scope

This does not test binary uploads, image delivery, external media servers,
previously issued token expiry, production object caching or process-failure
recovery. Raw project transfer/export and normal-adapter recovery remain migration
gates. No public library signature changes require harvester/tools adaptation.
