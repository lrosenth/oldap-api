# Reification model API

Stage 1B is implemented locally on `codex/reification-properties`.
The authenticated `/admin/datamodel/<project>/reifier-shape/<shape>` endpoint
supports GET, PUT (create), POST (replace supplied fields), and DELETE.
Model GET includes `reifierShapes`; property payloads include `reifierShapes`
and optional `reificationRequired`, preserving explicit false.

See [the library contract](../../oldaplib/docs/reification-stage1b.md) for
examples, omission/removal semantics, authorization, integrity checks and the
instance-write barrier. [OpenAPI](../API-def/oldap-api.yaml) defines the API
schemas. Legacy `annotationProperties` remains unchanged.

83 focused library/API tests and seven native Jena checks pass. API tests use
Flask and an isolated RDFLib dataset; native library tests use disposable TDB2.
No live service or deployment was changed. Use matching local library sources
for development; release dependency pinning remains a separate step.

Stage 2 acceptance now covers actual tools-driven shape and property CRUD,
false/zero/clear semantics, unchanged replay and model backups through these
Flask routes on both RDFLib and native Jena. See
[tools acceptance](../../oldap-tools/docs/reification-stage2.md).

## Instance lifecycle

Stage 3 now supports managed assertion annotations through explicit instance
operations; see [instance contract](reification-instances.md). The earlier
model-only write barrier is retained for unsupported paths such as transformations.
