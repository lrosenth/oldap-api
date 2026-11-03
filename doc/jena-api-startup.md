# Opt-in Jena API startup and model/list acceptance

## Status

The regular `create_app()` now selects `JenaConnection` when
`OLDAP_BACKEND=jena`. Omit the variable (or use `graphdb`) to retain GraphDB.
Unknown backend names and incomplete Jena settings fail before serving requests.
Existing HTTP routes and public library call signatures remain unchanged.
This is migration integration, not a production deployment or complete CRUD port.

All API-owned connection creation goes through `oldap_api/backend.py`, including
login, request authentication and service-user connections. The implementation
reuses the library's credential and JWT handling. `User.read` has a private query
hook so token refresh can read RDF 1.2 membership annotations.

## Configuration contract

The backend requires these explicitly supplied environment variables:

| Variable | Meaning |
| --- | --- |
| `OLDAP_BACKEND` | `jena` |
| `OLDAP_JENA_URL` | Private session service URL ending in `/tx`; not a stock Fuseki SPARQL endpoint |
| `OLDAP_JENA_SERVICE_KEY` | Matches service `PROBE_TRANSPORT_SECRET` |
| `OLDAP_JENA_BOOTSTRAP_KEY` | Matches service `PROBE_BOOTSTRAP_SECRET`; read-only credential bootstrap |
| `OLDAP_JENA_FULLTEXT_KEY` | Matches service `PROBE_FULLTEXT_ADMIN_SECRET` |
| `OLDAP_JENA_IDENTITY_KEY` | Matches service `PROBE_IDENTITY_SECRET` |
| `OLDAP_JENA_TIMEOUT` | Optional request timeout in seconds, default 60 |

Existing access/refresh JWT, authentication service user and isolated Redis
settings still apply. The service's `PROBE_IDENTITY_URL` points at this API's
`/internal/jena/identity`. This private form-POST endpoint verifies tokens with
`TokenCodec` without opening a database connection. Restrict it at a deployment
proxy; the endpoint also requires its separate service credential. Java receives
no JWT signing key. Use a threaded API server to allow verification callbacks.

A standalone persistent service is now built from sibling `oldaplib/services/jena`.
See [build, private configuration, lifecycle and acceptance](../../oldaplib/docs/migration/graphdb-to-jena-cutover.md#persistent-private-backend-service-implemented-2026-11-02).
The table's PROBE names describe only the historical test runner. For the service,
map API SERVICE_KEY -> serviceSecret, BOOTSTRAP_KEY -> bootstrapSecret,
FULLTEXT_KEY -> fulltextSecret and IDENTITY_KEY -> identitySecret in its private
properties file. Set identityUrl to this API's loopback `/internal/jena/identity`
endpoint and OLDAP_JENA_URL to the service's fixed loopback port plus `/tx`.
No JWT signing key is supplied to Java. Probe flags and fault headers cannot
enable test behavior in the production entry point. No shared service or API
configuration was switched by this implementation.

## Transaction behavior

Interactive Python model logic remains visible: BEGIN, queries/updates, COMMIT.
The transport never replays updates automatically. After a lost commit reply,
only the durable actor-bound STATUS receipt proves success. Unknown outcomes
retain transaction ownership; repeated commit checks STATUS only. A lost abort
reply also leaves the connection uncertain. Nested BEGIN is rejected.

GraphDB-specific clear/move/upload/inference maintenance methods explicitly
refuse operation in this adapter. General RDF-star writers are not rewritten
implicitly. Result decoding supports native JSON SELECT/ASK and JSON-LD
CONSTRUCT, with graph serialization to Turtle/N3/RDF XML; this is not a claim
of support for every GraphDB result-format combination.

## Reproducible owned acceptance

From this API repository, with the sibling tools environment installed:

```sh
.venv/bin/python tools/migration/probe_api_jena.py \
  --java /path/to/java \
  --jar /path/to/fuseki-server.jar \
  --output /new/empty/acceptance-directory
```

The runner creates its own dataset, random credentials, loopback ports and
synthetic users. It uses normal API startup and backend selection, without
replacing a connection factory. Only object-cache Redis I/O is suppressed;
therefore this does not prove Redis deployment behavior. List/model data is
seeded from the repository ontologies. Services stop on completion or failure.

The recorded run verifies:

- Startup, health, private identity boundary, wrong/right password and refresh.
- Model, class and property create/read/update/delete through existing routes.
- List/node CRUD, left/right/below moves, return to an ancestor, actual nested-set
  indices and requested child positions, plus rejected descendant moves.
- Managed fulltext activation through the regular authenticated connection.
- Real tools CLI import with activation last; subsequent model update with
  parse-validated TriG and fulltext snapshot; Jena YAML dump and unchanged
  dry-run imports with zero planned writes.

See `jena-api-startup-results.json` for the individual checks. API offline tests
cover the default GraphDB factory, invalid configuration, identity rejection,
authentication boundaries, existing fulltext/Lucene routes and worker startup.
Library tests cover receipt-only recovery, duplicate-BEGIN rejection, abort
uncertainty and prior authentication/transaction behavior.

## List corrections discovered by acceptance

The existing right-move implementation began a second transaction midway
through a move. That start is removed. Move updates now explicitly select the
list graph with `USING`, avoiding GraphDB's implicit union default graph. Two
right-index updates incorrectly bound `oldLeftIndex` to `rightIndex`; corrected.
The below-move interval calculation failed when moving back to an ancestor.
It now uses three documented steps: detach the subtree with negative indices,
close the old gap/open the new gap, then restore the subtree's relative indices.
Invalid descendant moves abort before raising. Public method signatures stay
unchanged. These are shared library corrections; live GraphDB regression was
not run. Exhaustive multi-level/concurrent list moves remain further acceptance.

## Next gates

- User/role writes are covered in `jena-user-writes.md`; ordinary resource writes
  and basic transformation are covered in `jena-resource-writes.md`. Continue
  with remaining bulk/copy/export paths and specialized value/workflow coverage.
- Broaden nested-set move coverage to multi-node subtrees and concurrency.
- Normal-adapter fulltext mutation/search/revision acceptance is documented in
  `jena-fulltext-writes.md`; production load and restart testing remain separate.
- Package the service and verify isolated Redis/cache and worker behavior.
- Keep production deployment, larger-dataset performance, broad inference,
  restart/recovery and untested maintenance formats explicit acceptance gates.
