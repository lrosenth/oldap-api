# Mixed private-folder inventory and catalogue retention

AS-03 adds `GET /data/{project}/staging-folder-inventory` to the existing archive
blueprint. Existing Bearer authentication and `Cache-Control: no-store` apply.

Query parameters are `folderIri` (absolute IRI, required), `limit` (1..100, default
50), and optional `cursor` (maximum 4096 characters). Unknown or duplicate
parameters are rejected. See the frozen `InventoryResponse` in
`doc/archive_structure_v1.schema.json` and `API-def/oldap-api.yaml`.

The response contains `folderIri`, `revision`, `entries`, `nextCursor` and `warnings`.
Entries are direct visible media, ordered by kind/IRI, with explicit `stagingMedia`
or `archiveReference` kinds and display capabilities. Reference metadata editing
and media deletion are always false. No hidden identifier/count is exposed.
Subfolder navigation and existing generic searches keep their current contracts.

Pass `nextCursor` unchanged for the next page. It is HMAC-protected and bound to
caller/project/folder/revision/last position. A changed folder returns 409
`STALE_FOLDER`; reload page one. Invalid/tampered/context-mismatched cursors return
400 `INVALID_REQUEST`. Visibility is checked afresh, including after role
revocation. The signing key is purpose-derived from the configured access-token
secret; its rotation invalidates cursors without creating a new auth mechanism.

The endpoint uses the existing additive `{code,message,requestId}` errors; auth
keeps legacy 401 `{message}`. Missing/forbidden resources produce 404/403 and
unavailable policy/coordination produces 503. Empty warnings currently mean no
public warning was emitted, not that every private edge was disclosed.

Catalogue retention is implemented in oldaplib's existing transform boundary.
The existing transform request fields and success response are unchanged; no
extra CaptureApp payload field or response identity is introduced. The backend
retains organisation read access and the current folder reference atomically,
including the protected Mobile inbox. A repeated old `expectedSourceClass`
conflicts with 409. Mobile upload-commit receipts replay unchanged after transfer
and private relocation. The accepted post-transfer note/clear 409 remains intact.

This does not enable the client workflow or mixed ZIP export. AS-04–AS-09 retain
those planned responsibilities. Read oldaplib `docs/private_repository_lifecycle.md`
and `docs/writer_recovery.md` before selecting the policy in a deployment.
