# Archive domain API — AS-02

The reusable domain policy and persistent coordination live in the accompanying
oldaplib source. Set `OLDAP_ARCHIVE_POLICY_FILE` only after the role/ACL migration,
Shared model load and durable writer-store deployment have been reviewed. Policy
selection also switches existing staging/mobile writer coordination to the shared
non-expiring gate. The old lease behavior remains when no policy is selected.

## Existing client contracts

The generic `POST /data/{project}/{instance}` endpoint retains its JSON `{message}`
response envelope. Typed invalid-value, permission, not-found and reference/
inconsistency failures return 400, 403, 404 and 409; coordination/configuration
failures return 503. Non-object bodies and unknown property keys (including null
and delta forms) are rejected. Clearing an absent known optional property remains
idempotent. Existing move-route requirements recognize transitive Shared classes.

With archive policy enabled, the update route rereads the current resource inside
the coordinated transaction and checks the preparation-note lifecycle **before**
model conversion or stale-class rejection. Writing or clearing the configured
note after cataloguing returns HTTP 409 with exactly:

```json
{"message":"Dieses Medium ist bereits archiviert. Die Vorbereitungsnotiz kann nicht mehr geändert werden."}
```

This applies even to combined roles/admins and targets without a note property.
Request formats, successful legacy response shapes and CaptureApp source remain
unchanged. Its maintainer remains responsible for native conflict presentation;
AS-08 includes native acceptance. Existing protected system-folder/area workflows
remain in place, with an extra empty-area check for references/default mappings.

## Additive v1 bindings

All four routes require existing Bearer authentication and return `no-store`:

| Route | Purpose |
| --- | --- |
| `GET /data/{project}/staging-folder-inventory` | Signed, visible mixed direct media pages (AS-03). |
| `GET /archive/{project}/structure/capabilities` | Enabled policy, structure capability, create capability and frozen size limits; never substitutes for per-resource authorization. |
| `POST /data/{project}/staging-reference-move` | Atomic private-reference move with UUID `Idempotency-Key`, source/target revisions and owner-scoped receipt. |
| `GET /archive/{project}/structure/operations/{operationId}` | Currently visible committed receipt belonging to this caller and project. |

The reference body contains exactly `mediaIri`, `sourceFolderIri`,
`targetFolderIri`, `sourceRevision`, `targetRevision`. IRIs are absolute and at most
2048 characters; revisions are lowercase SHA-256 hex. Maximum request size is
2,000,000 bytes. Success is the frozen `ReferenceMoveResponse` (200). Mixed
inventory/revision delivery is implemented in AS-03 (`staging_folder_inventory.md`); reviewed structure apply is AS-04.

New domain errors use `{code,message,requestId}`: invalid input/hierarchy 400,
forbidden 403, missing 404, stale/replay/reference conflicts 409, too large 413,
and unconfirmed coordination/backend outcomes 503. The authentication boundary
keeps its legacy 401 `{message}`. See `archive_structure_v1.schema.json` and
`API-def/oldap-api.yaml`. After an uncertain result, inspect the original receipt
and retain the original operation ID/body; do not blindly create another command.

## Verification and operational limits

Focused Flask tests validate the frozen response schemas, authorization, cache
headers, typed errors, size limits, malformed input and legacy update behavior.
Separate real-model GraphDB tests exercise role separation, post-transfer notes,
atomic rollback, direct-library contention, receipts and access revocation.
A guarded 500-unit transaction completed within the current 60-second default
Gunicorn timeout locally. This is evidence for the source implementation, not a
production throughput guarantee.

Read oldaplib `docs/archive_domain.md` and `docs/writer_recovery.md` before
activation. The current running Redis was not reconfigured; release, migration,
production recovery rehearsal and deployment remain AS-08/AS-09.

AS-03 adds the mixed inventory route and atomic retained-reference lifecycle. See
[private-folder inventory](staging_folder_inventory.md) for the new read binding
and unchanged transform/Capture boundaries.
