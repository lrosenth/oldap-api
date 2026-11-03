# Complete Fasnacht model import rehearsal

The `--fasnacht-only` mode of `tools/migration/probe_api_jena.py` provisions a fresh,
owned Jena dataset and normal API instance. `check_fasnacht_model.py` imports the
actual sibling `oldap-tools/fasnacht/fasnacht-onto.yaml` through the real CLI,
including its relative taxonomy files and external-ontology registrations.
GraphDB-specific Lucene connector creation is explicitly skipped. This does not
activate or validate the replacement Jena fulltext configuration.

The rehearsal verifies:

- Planning is read-only; the target project still does not exist afterward.
- Full import creates the declared classes, with only `isPartOf` on Place and
  CarnivalThing, and a direct `archiveUnit` assignment on ArchiveObject.
- Repeating the tools plan produces zero writes across model and taxonomies.
- Synthetic parent/child data passes the reviewed preflight and is converted
  from `hasPart` to `isPartOf` within one Jena transaction.
- The normal HTTP class-search route, as used by the public frontend, finds the
  permitted child and excludes the child without a grant.
- No legacy `hasPart` instance predicate remains in the selected data graph.

## Run

Use the existing API virtual environment and installed native Jena distribution:

```sh
.venv/bin/python tools/migration/probe_api_jena.py --fasnacht-only \
  --java /absolute/path/to/java \
  --jar /absolute/path/to/fuseki-server.jar \
  --output /absolute/path/to/new-private-output-directory
```

The output directory must not exist. It contains the owned dataset, source-plan
and import logs, initial-state snapshot and results. The full CLI import is given
a 15-minute deadline; individual HTTP requests retain their normal limits.
Listeners and owned Java processes are shut down by the runner's finally block.
Object-cache calls are suppressed; the user's Redis is not used.

## Boundaries

This is a fresh-target model and synthetic-data rehearsal, not a production
export migration. It does not establish parity for real Fasnacht instances,
in-place removal of obsolete shapes/restrictions, cross-project data, external
vocabulary graph loading, production cache behavior, fulltext or browser rendering.
The import registers external ontologies through the normal API; registration
alone is not proof that every external vocabulary triple was loaded.

The source repositories and live services are unchanged. See the central
[cutover guide](../../oldaplib/docs/migration/graphdb-to-jena-cutover.md) and the
[part-direction migration](../../oldaplib/docs/migration/fasnacht-parts.md).

## Result

2026-10-30: The actual migration YAML imports through tools/HTTP with 16 classes, 88 property declarations, 10 taxonomies and 3 external registrations. 224 operations, then zero-write replay. Canonical isPartOf reverse lookup excludes an ungranted child after transactional conversion. All 13 focused checks pass.

Source/taxonomy hashes and checks: [retained evidence](jena-fasnacht-model-results.json).
