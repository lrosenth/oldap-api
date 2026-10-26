# Structured Dating responses

Clients opt in with `Accept: application/json; dating=structured`. Instance reads
(`/data/...`), search results and media lookup serialization then retain OLDAP
Dating values as JSON objects. Without this parameter, legacy responses remain unchanged. The property's surrounding list/scalar shape
is unchanged. Other ordinary datatype and role serialization is unchanged.

```json
{
  "fasnacht:dating": [{
    "dateStart": [1515],
    "dateEnd": [1515],
    "datePrecision": "YEAR",
    "inCalendar": "GREGORIAN",
    "verbatimDate": "[um 1515]"
  }]
}
```

`dateStart`/`dateEnd` are calendar date tuples, with one, two or three components.
`datePrecision` and `inCalendar` use the existing enum names. A persisted date
also includes `iri`. `verbatimDate` is included when present; `before` contains
IRI references rather than recursive date graphs. Dates with no original wording
omit `verbatimDate`.

Legacy instance responses flatten dates to normalized strings, losing original
wording. Opt-in clients should prefer verbatim text for display and use tuples
and precision for sorting/filter inputs. FasnachtsPage requests this representation
centrally in `api_config.ts`; its existing detail/list/edit formatters support it.
A circa year remains a search anchor, not an invented uncertainty interval.
The legacy `/admin` resource serialization is unchanged.

Search normally returns Dating IRIs. For opted-in searches, the API identifies
requested Dating properties from the resource classes and resolves them through
reader-authorized summary reads in batches of at most 100 resources. Missing or
unreadable summaries omit their dating field. Other properties, ordering and
scores are preserved; count queries perform no expansion.

The OpenAPI `DatingValue` schema covers scalar and list-valued responses. Client
response validation must accept it before opting in.

Regression tests: `oldap_api/test/test_dating_serialization.py` and
`oldap_api/test/test_read_instance_fast_path.py` (no live GraphDB required).
