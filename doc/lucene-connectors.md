# Project Lucene connector administration

`GET /admin/lucene/{project}` returns `{name, configuration, revision}`. An existing
project with no connector returns HTTP 200 with null configuration and revision;
404 means missing project/route. Revision is SHA-256 over UTF-8 JSON with sorted
object keys, no whitespace, unescaped Unicode, preserving array order.

`PUT /admin/lucene/{project}` accepts `mode` (`create` or `replace`), native GraphDB
`configuration`, and `expectedRevision`. Replacement requires this field, including
explicit null to assert absence. Responses contain `name` and `status` (`created`,
`replaced`, `unchanged`). Create conflicts or stale revisions return 409, malformed
requests 400, missing authentication 401, insufficient project ADMIN_MODEL (or
system ADMIN_OLDAP) 403. Both reads and writes require model administration.

The endpoint manages only the connector named by the resolved project shortname.
It cannot issue arbitrary SPARQL or choose other connector names. All native
creation options are preserved. Matching replacements do not rebuild indexes.
The service validates structural input before dropping and attempts restoration
on creation failure; failure is HTTP 500 with recovery status. No mutation retry
is automatic. Index creation/replacement is not an RDF transaction and may require
reindexing. Advanced GraphDB option validity is checked by GraphDB during creation.

The full library operation joins the configured durable writer gate when archive
coordination is enabled. Deployments without it and external administrators must
serialize connector changes. Revision checks detect changes before execution but
are not a GraphDB compare-and-swap transaction. Unrelated search/data routes retain
their contracts. New API routes require the matching oldaplib Lucene service;
older installations return 503 for this feature while existing routes remain usable.
Publish paired releases before production; source-only development wheels must not
be treated as a published version guarantee.

Offline tests: `oldap_api/test/test_lucene_views.py`,
`oldap_api/test/test_authentication_boundary.py`, and oldaplib's
`oldaplib/test/test_lucene_connector.py`. Never exercise destructive index operations
on production as a regression test.

## Model restoration and external edits

Administrative datamodel JSON GET and TriG download bypass cached model objects.
This is essential when Workbench has deleted the ontology/SHACL graphs: a still
cached model must not suppress recreation during CLI planning. Connector presence
alone does not confirm that its required model has been restored. The regressions
in `oldap_api/test/test_datamodel_fresh_snapshot.py` cover external graph deletion
with stale cached state. Other entity caches and the writer-coordination store are
not cleared by this change.
