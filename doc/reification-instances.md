# Assertion annotations on instances

Stage 3 is implemented locally with matching oldaplib sources and an RDF 1.2
backend. See the [library lifecycle contract](../../oldaplib/docs/reification-stage3.md)
for validation, permissions, history, ownership and measured read/search behavior.

Use the existing creation route `PUT /data/{project}/{classIri}`:

```json
{
  "iri": "T",
  "travel:isAt": ["travel:A"],
  "@annotations": [
    {"op":"add", "property":"travel:isAt", "value":"travel:A",
     "fields":{"travel:dateTime":["2026-11-01T10:00:00Z"]}},
    {"op":"add", "property":"travel:isAt", "value":"travel:A",
     "fields":{"travel:dateTime":["2026-11-02T10:00:00Z"]}}
  ]
}
```

The response adds `annotationIris` in operation order when records were added.
Both visits refer to the same asserted base value and have independent IDs.
Creation accepts only `add` operations.

`GET /data/annotations/{project}/{instanceIri}` explicitly returns an `items` array.
Each item contains `iri`, `property`, typed RDF `value`, typed `fields`, `managed`
and `asserted`. A managed flag is diagnostic, not a guarantee of current write
permission or exclusive ownership. Datatype/language information is preserved.

Use the existing `POST /data/{project}/{instanceIri}` to apply base and annotation
changes atomically:

```json
{
  "@annotations": [
    {"op":"replace", "iri":"urn:uuid:ID-FROM-READ",
     "fields":{"travel:dateTime":["2026-11-01T11:00:00Z"]}}
  ]
}
```

Allowed operations are `add(property,value,fields)`, `replace(iri,fields)` and
`remove(iri)`. Keys are strict. Replace supplies the complete field set. Reads
return full IRIs; input accepts QNames where the connection knows their prefix.
Field values must be arrays. Scalar inputs are coerced by the model; explicit
SPARQL-style scalar term objects support `uri`, `literal`, `datatype`, `xml:lang`.
Blank nodes may be returned for diagnostics but are not writable.

Annotation edits require the parent's UPDATE permission (or its existing admin
exception). Cross-owner IDs and protected permission annotations are rejected.
Deletion of the parent cleans owned records. Required reification, stale-state
checks and ownership restrictions apply to every supported write path.

History items include `annotations` when their old group is nonempty. The existing
history restore route restores the complete property group under current
validation. Changed restored records receive new IDs, so refresh the explicit
annotation read after restoration.

Ordinary instance GET and search responses are unchanged and do not fetch
annotations. The API does not yet filter searches by annotation fields (stage 4).
Transforming annotated instances and instance-data YAML v1 writes are explicitly
unsupported. No live API service was changed as part of this implementation.

Annotation search is now implemented locally: see [stage 4](reification-search.md) for
same-reifier filters, explicit projection and unchanged ordinary search paths.
