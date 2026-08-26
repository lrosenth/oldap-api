# Permission-aware resource summaries

`POST /data/summaries/{project}` is an additive read endpoint for interactive
clients that need compact metadata for several known resource IRIs. It reduces
the common search/detail N+1 pattern without changing any existing endpoint or
response contract.

## Request

```http
POST /data/summaries/chama
Authorization: Bearer <access token>
Content-Type: application/json
```

```json
{
  "iris": ["chama:IMG_1751", "chama:PICT0111"],
  "includeProperties": ["schema:name", "shared:hasMediaObject"],
  "includeMediaDelivery": true
}
```

- `iris` is required and accepts 1–100 QNames or absolute IRIs. Repeated IRIs
  are collapsed at their first occurrence.
- `includeProperties` is optional and accepts at most 32 property QNames.
  Omitting it requests `schema:name`; an empty array requests type information
  only. `rdf:type` is always returned.
- `includeMediaDelivery` defaults to `false`. If enabled, the API may enrich a
  readable local IIIF media resource with a short-lived capability or return an
  external-image delivery description. Internal media-token source fields are
  not exposed unless explicitly requested through `includeProperties`.
- Unknown top-level request fields are rejected. Clients should split larger
  workloads into batches of at most 100 IRIs.

## Response

```json
{
  "resources": [
    {
      "iri": "chama:IMG_1751",
      "resclass": "chama:CataloguedPhotograph",
      "data": {
        "rdf:type": ["chama:CataloguedPhotograph"],
        "virtual:inferredTypes": ["shared:MediaObject"],
        "schema:name": ["K-36 #488 im Panorama"]
      },
      "mediaDelivery": {
        "kind": "iiif-image",
        "infoUrl": "https://media.example/iiif/3/IMG_1751/info.json",
        "capability": "<short-lived token>"
      }
    }
  ]
}
```

Readable resources retain their first-occurrence request order. Missing and
unreadable resources are both omitted, deliberately without an error or status
distinction. This prevents the batch endpoint from becoming an existence probe
for protected data. An empty `resources` array is therefore a valid response.

The `data` member uses the same value shapes as the established
`GET /data/{project}/{instiri}` response, but contains only the requested
properties, explicit `rdf:type`, and optional `virtual:inferredTypes`.
`resclass` names the most specific OLDAP resource class selected by the normal
resource factory.

`mediaDelivery` is optional and can be `null` when the resource is readable but
does not describe a supported image delivery or no applicable media permission
can be derived. IIIF capabilities remain short-lived authorization data and
must not be persisted or logged by clients.

## Performance and compatibility

The API delegates one bounded batch to
`ResourceInstanceFactory.read_summaries()`. OLDAP performs one
permission-filtered GraphDB `CONSTRUCT` for the requested resources and
properties, including the type and role facts needed for serialization and
optional media authorization. Datamodel construction may still use normal
OLDAP caches; there is no per-resource metadata query in this operation.

This endpoint is strictly additive. Existing single-resource, media lookup,
search, and full-text endpoints are unchanged. Clients may adopt summaries
incrementally and retain the single-resource routes for full editing forms or
complete record reads.
