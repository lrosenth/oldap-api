# Archive assignment: HTTP model migration acceptance

`fasnacht:archiveUnit` expresses a directly stored archival assignment;
`schema:about` remains an independent subject reference. The migration YAML uses
`inverse_of: null` to remove the old `owl:inverseOf` metadata. Omitting the key
would preserve it during incremental import.

## Reproducible owned acceptance

`tools/migration/check_archive_assignment.py` is called by
`tools/migration/probe_api_jena.py`. It uses the real API/backend factory, owned
Jena dataset, credentials and HTTP listeners. Object-cache I/O is suppressed;
no shared Redis, GraphDB or production data is accessed.

The fixture reads the target class, cardinality and explicit null from the actual
Fasnacht YAML. It applies these to an isolated `demo:ArchiveObject` model and
`demo:archiveUnit` field; it does not import the entire Fasnacht ontology.

1. Create the legacy inverse model through HTTP and two resources: one directly
   assigned object and one referenced only by a unit's `schema:about`.
2. Reproduce the unwanted inferred assignment through the ordinary resource API.
3. Use the real tools CLI to preview the YAML update, back up the previous model,
   and apply it through the existing HTTP model-update endpoint.
4. Verify model metadata and persisted RDF no longer contain the forward inverse
   axiom, while the target/cardinality and direct-resource response are preserved.
5. Verify the subject-only object no longer returns an archive assignment and
   all instance triples are identical before and after the schema update.
6. Preview the import again: it must plan zero writes.

No SPARQL schema cleanup substitutes for the model update under test. Direct
SPARQL is used only to seed owned subject/unit data and inspect persisted triples.
The private ZIP backup contains the previous JSON model and TriG, including the
legacy inverse axiom. It is a model snapshot, not a full data backup.

## Migration boundaries

The API modifies metadata owned by the property being edited. This acceptance
covers `archiveUnit owl:inverseOf schema:about`, the direction declared in the
Fasnacht YAML. It does not promise removal of a separately stored reverse axiom
on `schema:about` or one in an external vocabulary. Inspect both directions in
selected target ontology graphs before declaring the migration complete. The
native library fixture separately tests cleanup of both orientations.

Keep `schema:about` instance data and generic archive imports unchanged. Do not
turn subject links into assignments automatically. Existing live systems have
not been changed. Full Fasnacht import/real-data comparison, object-cache behavior
and general inverse-read-field acceptance remain separate gates.

See the [semantics profile](../../oldaplib/docs/migration/oldap-semantics-profile.md)
and [cutover index](../../oldaplib/docs/migration/graphdb-to-jena-cutover.md).

## Result

2026-10-30: **162 API integration checks pass**, including eight new archive
assignment checks. The private backup was also inspected for the previous JSON
metadata and RDF inverse axiom. See [retained results](jena-archive-assignment-results.json).
Owned processes completed successfully.
