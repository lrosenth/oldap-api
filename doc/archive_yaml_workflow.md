# Archive YAML HTTP workflow

The API exposes one read-only proposal download and one two-step create-only
import workflow. All operations use the authenticated request connection; no
general service account or model/list administration permission is involved.

## Endpoints

- `GET /archive/{project}/staging-proposal?stagingAreaIri=...` returns canonical
  YAML with editorial warnings as comments. Only visible Staging folders/media
  influence the result, and the request performs no writes.
- `POST /archive/{project}/imports/preflight` accepts a JSON `yaml` string or a
  multipart `file`. It validates the 2 MB limit, safe YAML version 1 schema,
  semantics, IDs, deterministic IRIs, references, collisions, attachment
  points, permissions, and the maximum 5,000 units. It returns ordered units
  and the exact document SHA-256 without writing.
- `POST /archive/{project}/imports/apply` accepts JSON `yaml`, the preflight
  `documentHash`, and `confirm: true`. It rejects text/hash divergence, repeats
  preflight against current data and permissions, then creates parents before
  children through `oldaplib`.

Creating new ArchiveUnits requires `ADMIN_CREATE`. Attaching below an existing
ArchiveUnit additionally requires `DATA_UPDATE` on that visible parent.
`DATA_VIEW` governs reads and references. There is no `ADMIN_ARCHIVE`, and
neither `ADMIN_MODEL` nor `ADMIN_LISTS` is used.

Imports never update, merge, move, or delete an existing ArchiveUnit. On create
failure, completed nodes are deleted in reverse order where possible; HTTP
errors explicitly report rollback failures. Successful apply events log the
authenticated user, project, document hash, result, and created count.
