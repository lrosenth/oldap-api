# RDF 1.2 archive publication

## Scope and behavior

`ArchivePublication` now reads grant annotations with RDF 1.2 on Jena for both
publication reviews and additive parent-link reviews. GraphDB retains its
existing syntax. Reifier identifiers are not projected into review hashes;
permission values, asserted memberships and resource metadata remain part of
the reviewed state.

The Jena publication write follows three visible steps inside the existing
resource transaction:

1. Reject a resource permission reifier describing multiple memberships. Such
   imported data must be separated before editing; the service raises the existing
   `PublicationConflict` (HTTP envelope: `PUBLICATION_CONFLICT`, 409).
2. Remove only the public role's old permission annotations, preserving other
   roles and unrelated reifier metadata.
3. Set the status, public membership and modification metadata; add one explicit
   reifier with the selected public permission.

The command writes its actor-scoped receipt after all resources. A failure at
any point aborts the entire command, including earlier resource writes and the
receipt. The existing private helper `clear_membership_annotations` accepts an
optional serialized target for this narrow cleanup; its default whole-map
behavior remains unchanged for users and ordinary resource mutations.

Public API/library signatures, publisher-role checks, data-update requirements,
resource limits, stale-review rejection, dependency restrictions, retry semantics
and the prohibition on widening existing published access are unchanged.

## Validation boundary

The owned acceptance stage `tools/migration/check_publication.py` creates real
models and resources through the normal API and runs the actual publication
service on the normal Jena connection. It uses an ordinary publisher with UPDATE
rights. The fixture supplies a server policy explicitly through a small subclass;
it does not activate the complete archive policy file or its staging/domain
coordination. Publication configuration references are validated against real
roles and model definitions. Query, authorization, model loading, transaction,
mutation and receipt implementations are not replaced. As in earlier acceptance
stages, Redis object-cache I/O is suppressed.

Checks cover root/media publication, annotation-only stale reviews, failure on a
shared reifier on the second resource after the first resource update, complete
rollback with no receipt, preservation of internal grants and annotation metadata,
exact replay and conflicting operation IDs, additive parent links, restricted
re-publication and fresh publisher membership. Offline regressions run the
existing domain decisions with both backend modes and verify targeted cleanup.

This is publication-service acceptance, not an end-to-end archive deployment.
Full policy-file loading, HTTP publication routing, mutation-gate/Redis behavior,
archive inventory/adoption/repository snapshot queries and complete export jobs
remain separate migration gates. No shared services or data are modified.

## Results

The retained `jena-publication-results.json` contains 102 passing checks: the
previous 91 and 11 publication/link checks. The targeted library suite passes
50 tests plus 14 subtests; API route regressions pass 15 tests plus 13 subtests. An initial fixture run rejected an incomplete shared
property definition; the fixture now models the common status on a base class.
No application validation was relaxed. GraphDB coverage is offline only.
