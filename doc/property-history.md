# Property history API

History exposes previous complete property value sets for currently readable
`oldap:Thing` instances. It includes modeled business properties of any namespace
and excludes internal metadata and role grants. Creation and existing instances
start with no entries; actual subsequent edits create history automatically.

## List

`GET /data/history/{project}/{instanceIri}`

Query parameters: optional `property` (QName or full IRI), `limit` (1–1000,
default 100), `offset` (nonnegative, default 0). Encode path/query IRIs normally.
The static `history` prefix avoids ambiguity with legacy instance routes,
including instance IRIs containing slashes.

```json
{
  "items": [{
    "iri": "urn:uuid:...",
    "timestamp": "2026-11-11T10:00:00+01:00",
    "userIri": "https://example.org/users/editor",
    "instanceIri": "fasnacht:example",
    "propertyIri": "schema:name",
    "values": ["Previous title@en", "Früherer Titel@de"]
  }],
  "limit": 100,
  "offset": 0
}
```

Entries are newest first. Paging counts complete entries, not individual values.
An empty `values` array means that the property previously had no value.
Values follow the existing instance JSON conventions; use
`Accept: application/json; dating=structured` for structured Dating display.
Restore always uses the typed stored values, never this display serialization.
Listing all pages is supported; paging is not a frozen snapshot across requests.

## Restore

`POST /data/history/{project}/{instanceIri}/restore`

```json
{"historyIri": "urn:uuid:..."}
```

Success: HTTP 200 with the ordinary update or move response. Ordinary properties
return `{"message": "Instance successfully updated"}`.
The referenced entry must belong to this project and instance. It supplies only
the value set: the ordinary update pipeline checks current permissions, model
constraints, archive policy, Staging restrictions and lifecycle hooks. Errors
retain the normal 400/403/404/409/503 semantics. Unsupported current properties
cannot be restored. Archive parent/position and Staging-folder parent restoration
use the existing dedicated move commands, retaining their cycle, area, ordering,
and system-folder protections. Other properties use the generic update command.

The caller must currently be able to read the instance and make the resulting
change. Current view permission also exposes past values. Restoring a value is a
new edit; the replaced state is itself retained. System properties cannot be
selected by the request or restored from forged history metadata.

Implementation: `oldaplib.src.resource_history.ResourceHistory` owns storage and
read checks. Manual and history updates share `_update_instance_data` and the archive/Staging
move handlers in `instance_views.py`. The history lookup precedes that pipeline; entries are
immutable, and the ordinary mutation re-reads the instance and checks write
permissions. API/library must be released together. This change does not publish
packages, restart services or deploy to home/production.

## Home deployment

On 2026-11-11, the property-history candidate and additive OLDAP ontology update
were deployed to home.org. See `../oldap-setup/docs/property-history-home-20261111.md`
(relative to the repository root) for the exact image, scope and recovery paths.
Production promotion and frontend integration remain separate.

## Production deployment

Later on 2026-11-11, the exact home image and additive ontology patch were also
deployed to production. Deployment and rollback details are in
`../oldap-setup/docs/property-history-production-20261111.md` (relative to the
repository root). Frontend integration remains separate.
