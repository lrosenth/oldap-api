# Jena resource writes and object permissions

## Implemented scope

The explicit Jena connection now supports the existing resource create, update,
class transformation and delete operations with RDF 1.2 object grants. HTTP
routes, request shapes, public method signatures and transaction callbacks remain
unchanged. GraphDB keeps the existing RDF-star branches by default.

`ResourceInstance.get_data_permission` selects the annotation dialect while
retaining the asserted resource-to-role link, project graph, current user's role
membership, permission threshold and creator exception. It reads through the
active transaction when one exists.

## Implementation and transaction ownership

`oldaplib/src/helpers/jena_permission_write.py` is the shared permission boundary
for user and resource grants. It replaces the former user-only helper module;
this internal rename is not a public API migration. The helper accepts an
explicit graph for resource writes, while user writes retain `oldap:admin`.
Only declared permission predicates are managed. Domain authorization and
transaction ownership remain in User and ResourceInstance.

- Creation writes ordinary properties, asserted role links and explicit UUID
  reifiers inside the existing resource operation transaction.
- Updates replace only a changed role map. Permission checks still precede
  mutation. The existing modified-timestamp verification aborts stale updates,
  including property writes that have already run inside that transaction.
- Transformations use the same grant replacement while retaining existing class,
  property, permission and optional link/callback checks.
- Deletion clears owned grant annotations and subject triples in the selected
  project data graph. Existing reference checks remain in place.
- Empty role maps remove membership and grant permissions. Multiple reifiers for
  one grant are cleaned together. Unrelated annotation metadata is preserved.
- A reifier describing multiple membership triples is rejected before grant
  changes or deletion. API deletion now maps this inconsistency to HTTP 409,
  matching update/transform conflict handling.

The resource-operation decorator still owns or joins the transaction. There is
no automatic update replay and no hidden commit inside the new helpers. A failed
callback or later operation rolls back the enclosing transaction.

## Acceptance evidence

`tools/migration/check_resource_writes.py` extends the normal API/Jena runner.
Run `tools/migration/probe_api_jena.py` as documented in `jena-api-startup.md`.
The retained `jena-resource-writes-results.json` includes all preceding startup,
model/list, tools and user acceptance checks plus this resource stage.

The new tests cover actual API calls and real library operations:

- Creation with RDF 1.2 grants, duplicate IRI rejection and denied creation for a
  user with role membership but no ADMIN_CREATE permission.
- DATA_VIEW cannot update/delete; DATA_UPDATE can change content but cannot
  elevate object permissions; DATA_PERMISSIONS can change content and grants
  atomically; DATA_DELETE can delete the object.
- A stale resource update and failures in update/delete callbacks roll back.
- A composed transaction with an earlier create and later duplicate create
  rolls back the earlier object too.
- A grant in a foreign graph cannot authorize a project-data write. Removing
  an asserted role link denies access even while its reifier remains.
- Class transformation preserves base properties and commits target class,
  target-specific values and replacement grants.
- Shared reifiers reject permission edits and deletion before changing data.
- Empty grant maps revoke access. Deletion removes the resource's grant links
  while preserving identical grant terms in a foreign graph.

The owned fixture now includes the standard six data-permission numeric values
from the administration ontology. No real administration credentials are loaded.
The root fixture has an explicit role membership because `factory.read()` retains
its existing role-based access contract; administrator privileges alone do not
bypass that read. `read_data()` and class-level `read()` retain their existing
creator-access behavior. This migration does not change those distinctions.

Offline tests verify default GraphDB permission syntax, opt-in Jena syntax,
transaction-local query routing, graph-scoped empty grant replacement and prior
resource/authentication/API behavior. Object-cache Redis I/O is mocked only in
the owned runner; no live GraphDB regression or operational cache claim is made.

## Remaining acceptance gates

This covers ordinary resource operations and a basic class transformation. It
does not establish parity for every dating/list/media/archive value, linked class
transformation, structural audit/outbox workflow or external harvester writer.
Remaining bulk/copy/export queries still contain legacy RDF-star syntax and must
be inventoried and ported separately. Normal-adapter fulltext effects of actual writes are now covered in
`jena-fulltext-writes.md`. Broader inference, deployment packaging, cache behavior
and large-dataset/recovery testing remain open.
