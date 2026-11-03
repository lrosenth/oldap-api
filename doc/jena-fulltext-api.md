# Managed Jena fulltext administration

`GET /admin/fulltext/{project}` and `PUT /admin/fulltext/{project}` are additive
routes. Existing routes, payloads and oldaplib public signatures are unchanged.
The OpenAPI definition includes the new state/configuration schemas.

## Connection and authorization boundary

The route uses the authenticated request's connection. It cannot select another
backend URL from JSON or an independent API environment variable. A Jena adapter
must explicitly enable `_managed_fulltext` and implement `_fulltext_admin` using
its same dataset-bound authenticated transport, with no automatic retries.
The default IConnection/GraphDB implementation refuses support with HTTP 503.
**Normal API startup still uses GraphDB Connection**: adding these routes does
not switch the application to Jena. Production transport selection, credential
bootstrap and remaining model-writer compatibility are separate migration work.

`oldaplib.src.project_fulltext.ProjectFulltext` reads the project with
`ignore_cache=True`, derives its authoritative data graph, and queries current
RDF for an active user plus either project ADMIN_MODEL or system ADMIN_OLDAP.
It requires both asserted membership and the RDF 1.2 permission reifier; token
claims or an orphaned permission annotation are insufficient. Both GET and PUT
use this authorization. Cache I/O is suppressed only in isolated tests.
Authorization is checked at the request boundary, not atomically with a later
index publication. It does not retrospectively cancel an already-authorized
request when permissions change concurrently.

The private service maintenance key stays server-side. It is not returned to
clients and is not a replacement for the public model-administration check.

## Contract

GET returns project, configuration, revision and status. Configuration is null
with null revision and status `absent`, or contains graph/fields with a canonical
UUID revision and status `active`. Every response is `Cache-Control: no-store`.

PUT requires exactly:

```json
{
  "configuration": {
    "graph": "https://example.org/demo/data",
    "fields": {"title": ["https://schema.org/name"]}
  },
  "expectedRevision": null
}
```

Null revision asserts initial absence; replacement uses the revision previously
read. Predicates must be full IRIs, fields nonempty, at most 256 fields and 16
predicates/path. The graph must match the project's namespace plus `data`.
Native GraphDB options and caller-supplied backend URLs are rejected.

A successful PUT returns the active state after a synchronous rebuild (or the
unchanged state for identical configuration). 400 denotes bad configuration,
401 missing/invalid authentication, 403 denied current rights, 404 missing
project, 409 revision conflict/busy backend, and 503 unavailable/uncertain state.
Do not automatically retry mutation requests. After uncertainty, inspect current
state; the backend may require a controlled restart before it can answer.

## Tools integration

For an existing project on an API with a bound Jena adapter:

```sh
.venv/bin/oldap-tools --api http://localhost:8000 --user USER ontology load \
  --inf ontology.yaml --fulltext apply --dry-run
.venv/bin/oldap-tools --api http://localhost:8000 --user USER ontology load \
  --inf ontology.yaml --fulltext apply
.venv/bin/oldap-tools --api http://localhost:8000 --user USER ontology dump demo \
  --search-backend jena --out ontology-export.yaml
```

These are usage examples, not a claim that localhost currently serves Jena.
The importer reads the fulltext endpoint before executing any model/list writes.
A 403/404/503 is an error, never interpreted as an absent index. It activates
fulltext last, with the reviewed revision, and includes `fulltext.json` in the
API ZIP snapshot. A failed final activation does not roll back earlier API
model/list transactions; the existing progress report identifies committed
operations. New projects must be provisioned first, then imported with fulltext.
Defaults keep GraphDB behavior and reject portable fulltext without explicit
`--fulltext apply`. Direct GraphDB imports remain guarded. Jena dumps preserve
full field IRIs and paths in `ontology.fulltext.fields`; they do not contact the
GraphDB Lucene route. Snapshots do not implement automatic restore or replace
whole-dataset backups.

## Evidence and limits

- 46 owned Fuseki/TDB2 integration checks in
  `../oldaplib/tools/migration/probe_fulltext_activation.py`, including the real
  Flask blueprint, real Project.read and fresh RDF permission checks. The API
  Connection factory is replaced with the tested Jena adapter; backend token
  verification remains real, and no shared Redis is used.
- 21 API authentication/Lucene/fulltext contract tests pass.
- 76 tools validation/import/backup/dump tests plus three subtests pass. The
  importer/model/list endpoints use fixtures in these offline tests; this is not
  a complete live Jena ontology CRUD migration.

The initial probe exposed an existing oldaplib IRI limitation: a synthetic
`urn:demo-project` was interpreted as a QName when reserialized. The fixture now
uses an HTTP project IRI consistent with current OLDAP deployments. General URN
identity support was not changed or claimed by this step.

Next: connect a supported Jena application transport to normal API startup and
exercise real model/list writes and search consumers together. Large rebuild
latency, public deployment and full RDF/index backup/recovery remain separate
acceptance work. No live service was switched, and no production data changed.
