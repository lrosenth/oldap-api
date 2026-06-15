### Update 2026-06-15 12:41
- Decisions: Treat `oldap:passwordResetRequestAt` as a built-in User API field, not an `additionalProperties` extension; expose `schema:email` as a first-class user search filter.
- Implementation: Added create/read/update serialization for `passwordResetRequestAt`, including `null` clearing on update; passed `email` through `/admin/user/search`; documented the fields in `API-def/oldap-api.yaml`; added focused regression tests; made `hasRole` add robust after all roles were removed.
- Open: Regenerate downstream clients from the OpenAPI contract where used.
- Risks/Assumptions: Requires an `oldaplib` version whose `UserAttr` includes `PASSWORD_RESET_REQUEST_AT` and whose `User.search()` accepts `email`.

### Update 2026-06-12 22:24
- Decisions: Expose oldaplib's structured `CompOp.NOT_EXISTS` search through the instance search API as a normal property filter operator.
- Implementation: Added NOT_EXISTS parsing in `parse_search_filter_items`, defaulting the filter value to the checked property QName when omitted; documented the operator in `doc/search_instance.md`; added an OpenAPI `SearchFilterItem` schema and wired it into both structured search endpoints.
- Open: Regenerate downstream clients from `API-def/oldap-api.yaml`; deploy with an oldaplib version that includes `CompOp.NOT_EXISTS`.
- Risks/Assumptions: The currently locked oldaplib release in this API environment may not yet include NOT_EXISTS; runtime search requires the updated sibling/package version.

### Update 2026-06-10 00:50
- Decisions: Expose the shared local/external MediaObject access contract through the media lookup API and OpenAPI schema.
- Implementation: Added explicit MediaObject JSON response shaping, updated MediaObject test payloads for required `shared:mediaAccessMode`, added external HTTP media lookup coverage, and documented `shared:mediaAccessMode`, `shared:mediaUrl`, and `shared:thumbnailUrl` in `oldap-api.yaml`.
- Open: Regenerate downstream clients from `API-def/oldap-api.yaml` where needed.
- Risks/Assumptions: Requires an `oldaplib` version that returns `shared:mediaAccessMode`, `shared:mediaUrl`, and `shared:thumbnailUrl`, plus migrated existing MediaObjects.

### Update 2026-06-09 00:09
- Decisions: Expose OLDAP resource-class transformation as a generic instance endpoint, not as project-specific Staging-to-Archive code.
- Implementation: Added `POST /data/{project}/{instiri}/transform`, delegating to `ResourceInstance.transform_class()` with `targetClass`, `preserveClass`, optional `expectedSourceClass`, target properties, and optional role replacement. Documented the contract in `API-def/oldap-api.yaml`.
- Open: Regenerate downstream typed clients and connect FasnachtsPage staging publish to the new endpoint.
- Risks/Assumptions: Requires an `oldaplib` version containing `ResourceInstance.transform_class()`.

### Update 2026-06-06 00:23
- Decisions: Document the instance permission update contract in the OpenAPI spec after adding `oldap:attachedToRole` mutation support.
- Implementation: Added `InstanceCreateData`, `InstanceUpdateData`, `AttachedToRoleUpdate`, and `AttachedToRoleDelete` schemas to `API-def/oldap-api.yaml`; updated `/data/{project}/{resclass}` and `/data/{project}/{instiri}` request bodies with examples; documented the contract in `codex.md`.
- Open: Regenerate downstream typed clients from `API-def/oldap-api.yaml` where projects consume generated schemas.
- Risks/Assumptions: The instance payload remains ontology-driven via `additionalProperties: true`; only the OLDAP permission map is modeled explicitly.

### Update 2026-05-26 14:45
- Decisions: Keep `rdf:type` backward compatible by returning only explicit resource type assertions from the project data graph. Expose reasoning-derived types separately as `virtual:inferredTypes`.
- Implementation: Updated instance read response shaping, OpenAPI `InstanceData`, and the read-instance regression test.
- Open: None.
- Risks/Assumptions: Assumes explicit `rdf:type` assertions in the project data graph represent the API-compatible resource class contract.
