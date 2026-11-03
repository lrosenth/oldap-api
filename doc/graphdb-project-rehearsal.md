# GraphDB project migration rehearsal: Chama

**Follow-up:** [Bounded entailment acceptance](jena-bounded-entailment.md) resolves
the 35 differences below. All original 112 and eight additional comparisons now
match; this document retains the initial findings and export workflow.

On 2026-10-29, exported the local GraphDB `oldap` repository's Chama project,
converted its legacy RDF-star and imported it through the protected project
transfer into an owned Jena TDB2 dataset. Compared normal HTTP API responses
against the existing GraphDB-backed API. **Transfer succeeds; content parity is
not yet complete.** See [sanitized results](graphdb-project-rehearsal-results.json).

## Scope and result

- Four selected project graphs: `data`, `onto`, `shacl`, `lists` (lists empty).
  Export is 120,663 bytes: 1,732 ordinary quads and 54 permission annotations.
- Converted 54 resource membership grants with zero orphans and zero added
  memberships. Native serialization verification preserves global blank-node
  identity. The existing 256 KiB HTTP request bound was sufficient.
- 54 resource identities from 17 classes: photographs, people, places, railway
  entities, knowledge contributions, stories, archive units and staging objects.
  Ten auxiliary Dating nodes are included in the data and hydrated responses;
  they are not independent resource endpoint requests.
- 112 comparisons: project metadata, complete data model and every identified
  resource, each as configured administrator and anonymous pseudo-user.
- All 112 HTTP statuses match. Administrator: 56 successful reads. Anonymous:
  34 successful reads and 22 HTTP 404 responses for hidden resources.
- 77 normalized response bodies match; 35 differ. All JSON fields and values are
  compared, with dictionaries and arrays normalized for order. This establishes
  unordered RDF-value parity, not API array-order/UI-order parity.
- Source project/schema/admin exports remain byte-identical when reread; all
  source API responses also remain identical. These bracketing checks are not a
  coordinated snapshot or a substitute for a cutover write freeze.

## Remaining differences and their cause

The final run includes the original base/shared schemas **and** all three
existing `urn:oldap:vocab:*` graphs (schema.org, Dublin Core, SKOS). Importing these
alone does not resolve the differences: current Jena resource queries merge only
project/shared/base `onto` graphs and derive `rdfs:subClassOf+` from that subset.

1. `virtual:inferredTypes` differs in 27 responses: missing `schema:Thing`, and
   additionally `foaf:Person` for people. The source schema.org vocabulary asserts
   superclass links and `schema:Person owl:equivalentClass foaf:Person`.
2. `chama:hasKnowledgeContribution` is absent in eight responses (four photographs,
   two actors). The project ontology declares its inverse `chama:describes`; the
   forward descriptions are asserted, the photo's backlink is GraphDB-derived.
3. `schema:hasPart` is absent in one administrator response for a story. The
   project declares `schema:isPartOf` as its inverse. This response also differs
   in inferred types, so field counts overlap.

This is an observed reliance on specific OWL axioms, not a need established for a
general OWL reasoner. Next implement deliberate, scoped read semantics for inverse
properties, external vocabulary hierarchies and class equivalences, consistently
across resource reads, summaries and search where applicable. Preserve asserted
versus inferred types; do not turn inferred source triples into asserted imports.
Re-run the same comparison; do not accept the current differences as success.
No application read query or public API signature was changed during this step.

## Provisioning and isolation

`tools/migration/probe_graphdb_project.py` reads GraphDB with `infer=false`, exports
all project graphs in one TriG-star request and retains the original export. It
separately provisions source schemas/vocabularies, project/role/permission registry
objects and only the configured administrator and anonymous account, including
RDF-star annotations. Administrative conversion produces 14 membership reifiers;
two pre-existing orphan annotations are retained without inventing memberships.
This limited bootstrap is not a general account migration implementation.

The target uses normal `create_app`, JenaConnection, fresh private signing/service
keys, own ephemeral loopback ports and own TDB2 files. Project import uses the
existing root-protected `_project_graph_import` transaction. Redis is a separate
socket-only owned process with separate cache/coordination databases: no cache
mocking in the final run. All owned processes stop on success or failure. The
existing source API, GraphDB and user's Redis instances are not reconfigured or
flushed. Source access consists of exports, queries, reads and login requests.

Private exports, account hashes, datasets, API bodies and detailed diffs are kept
outside Git under `~/Library/Application Support/OLDAP-Jena/probes/j27-chama-05/`.
The runner creates its output privately and refuses an existing directory. Never
publish these private artifacts. The repository retains aggregate evidence only.

## Findings corrected in the migration tooling

- The generic Jena dataset tuple-isomorphism check exceeded 90 seconds on this
  small real SHACL model. Verification now represents quads as rows in one
  temporary graph and uses the graph matcher. It preserves cross-graph blank-node
  identity, including blank graph names. The actual conversion/verification then
  completed in under one second locally; this is not an API performance benchmark.
- GraphDB's ordinary N-Triples CONSTRUCT export encodes RDF-star subjects as
  `urn:rdf4j:triple:` URIs. Administrative export now explicitly requests Turtle-star
  and retains its prologue outside the named graph wrapper. The converter rejects
  encoded triple URIs instead of silently treating them as ordinary resources.
- 28 native conversion checks and eight CLI checks pass, including negative
  checks for split blank-node identity, altered graphs/predicates/values and the
  encoded-triple refusal. These test results do not erase the API differences.

## Reproduce

From the migration API checkout, using its virtual environment:

```sh
.venv/bin/python tools/migration/probe_graphdb_project.py \
  --java /path/to/java \
  --jar /path/to/fuseki-server.jar \
  --source-config /path/to/original/oldap-api/.env.local \
  --output /path/to/new-private-rehearsal-directory \
  --project chama
```

Defaults are GraphDB `http://localhost:7200`, repository `oldap`, source API
`http://localhost:8000`. Credentials are read from the supplied local configuration,
not passed on the command line. Requires local `redis-server`, the migration
library sibling checkout and native Jena 6.2.0 tooling. A nonzero exit is intentional
while any response difference or source stability failure remains; inspect private
`results.json` and `differences.json`. Do not retry against an existing target.

Fulltext activation/rebuilding, binary media delivery, application archive policy,
ordinary/restricted/revoked named users, writes, large exports, crash recovery and
coordinated production snapshots remain separate acceptance gates. The source API
uses its existing cache; this rehearsal does not establish source cache freshness
against every source triple. Project graph blank-node sharing is preserved; the
separately exported bootstrap groups do not prove arbitrary cross-package sharing.
