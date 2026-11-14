# Assertion annotation search

Stage 4 adds opt-in `annotationFilter` groups and `includeAnnotations` to POST
`/data/search/{project}` and `/data/search/{project}/class/{resclass}`.

See the [complete library/API contract](../../oldaplib/docs/reification-stage4.md)
for Python/JSON examples, same-reifier and same-value semantics, absence behavior,
permissions, projection cost and performance evidence. OpenAPI describes both
structured-search request bodies and the strict group/field schemas.

Ordinary searches retain their query/payload contract. All annotation groups use
AND; comparisons within a group target one reifier. Annotation filters require a
class model and the RDF 1.2 backend. Explicit projection returns all groups of the
selected page, not only matched records, and is ignored for counts. GET/text routes
do not accept the new options. Annotation sorting/fulltext/aggregation are deferred.

Implementation and acceptance are local; no service was activated or deployed.
