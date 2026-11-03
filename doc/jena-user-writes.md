# Jena user and role write acceptance

## Implemented boundary

The normal Jena API now supports user create/read/update/delete, project
membership/admin permissions and role membership/default data permissions.
The existing role create/read/update/delete routes also pass against Jena;
role definitions themselves required no RDF-star query conversion.

Public HTTP request bodies and library method signatures are unchanged. The
private `_user_permissions_rdf12` capability is enabled only by JenaConnection.
GraphDB continues using its existing RDF-star serialization and update path.
`User.trig_to_str` emits the selected backend's syntax; Jena exports use explicit
RDF 1.2 reifiers with fresh UUID identifiers. Reifier identity is internal, not a
stable caller identifier.

## Readable write sequence

`oldaplib/src/helpers/jena_permission_write.py` contains only membership serialization
and update helpers; User retains authorization, validation, transaction ownership,
optimistic modified timestamps and authentication-version handling.

1. User creation asserts ordinary project/role memberships and writes explicit
   reifiers carrying their permission values.
2. An update validates existing projects/roles and the stored modified timestamp
   inside the original transaction. Only changed membership maps are replaced.
3. Replacement removes all old permission values, including duplicate reifiers,
   removes annotation-free reification links, and writes the desired memberships
   and grants. A membership with no permission values remains asserted.
4. Authentication-version and modified-timestamp checks still complete before
   commit. Invalid targets or stale updates abort the entire change.
5. Deletion removes user triples and owned grants in `oldap:admin` atomically.
   It does not delete triples in other graphs or another user's memberships.

Unrelated annotations on old reifiers are preserved as historical metadata, with
permission values removed. RDF 1.2 permits one reifier to describe several triples;
OLDAP does not infer which membership an annotation should affect. Updates and
deletes detect this within the transaction and reject it with
`OldapErrorInconsistency` / HTTP 409 before writing. Such imported grants must be
separated explicitly. This prevents modifying another membership's rights.

## Evidence

`tools/migration/check_user_writes.py` extends the existing owned
`probe_api_jena.py` runner. See `jena-api-startup.md` for invocation and isolation.
The new tests use real routes, library logic and Jena transactions, with only
object-cache Redis I/O suppressed. The retained `jena-user-writes-results.json`
includes all previous model/list/tools checks plus user/role checks.

The user checks cover:

- Role creation, label update, reading and deletion after unassignment.
- User creation and authentication using persisted RDF 1.2 permissions.
- Scalar and permission changes committed together; authVersion increment.
- Stale object rejection and complete rollback for unknown roles/projects.
- Empty project permissions versus removing the project membership entirely.
- Duplicate grant cleanup and preservation of unrelated annotations.
- Rejection of shared reifiers for both update and delete.
- Denial of profile changes by a user without administrative permission.
- User deletion with grants still present; isolation of other users and graphs.

Offline library tests also verify unchanged GraphDB user serialization and the
opt-in RDF 1.2 representation. Existing authentication and transaction tests pass.
A live GraphDB acceptance run was not performed.

## Remaining scope

Ordinary resource-instance writes are now covered in `jena-resource-writes.md`. This work
does not claim that all data CRUD paths, custom user subclasses/properties,
refresh-cookie revocation scenarios or external harvester writes are migrated.
Existing access-token lifetime semantics are unchanged. The original TODO about
references to a deleted user remains; this step does not introduce cascading
deletion of data owned by a user. Service packaging and isolated Redis operational
acceptance remain separate gates.
