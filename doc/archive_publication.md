# Project-configured publication API

Authenticated, no-store endpoints under `/archive/{project}/publication`:

- GET `capabilities` (optional `resourceIri`): configured feature/role availability;
  resource-specific checks restrict the UI to configured classes.
- POST `preview`: `{resourceIri, permission}`. Only DATA_VIEW/DATA_RESTRICTED.
  Returns root, revision and affected resource IRIs/effective public permissions.
- POST `apply`: same body plus `revision`, with UUID `Idempotency-Key` header.
  Commits the complete reviewed set and actor-scoped receipt atomically.
- GET `operations/{operationId}`: owner-scoped confirmed result, rechecking current
  publisher membership and visibility; 404 is not proof that an in-flight call failed.

The service in oldaplib resolves classes, roles, status and media-to-root relation
from `projects.<project>.publication` in OLDAP_ARCHIVE_POLICY_FILE. No project names
or vocabularies are embedded in backend code. Public schema: API-def/oldap-api.yaml.
Existing metadata/create/transform and CaptureApp contracts are unchanged; opted-in
publication status and public ACL changes are protected against generic CRUD bypass.

Matching oldaplib is mandatory before enabling the policy. Stage compatible API,
frontends and all direct-library writers before opt-in. The 0.7.18 published library
does not provide the new service. See the sibling FasnachtsPage
`docs/permissions/archive-roles.md` for role semantics and coordinated release steps.
No policy activation or ontology migration accompanies this source change.
