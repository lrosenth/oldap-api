# CODEX_LOG

### Update 2026-08-01 00:29
- Decisions: Expose one dedicated archive move command instead of duplicating tree reads or hierarchy logic in Flask; require archive parent/position changes to pass through this command.
- Implementation: Added `POST /data/{project}/{instiri}/archive-move`, explicit payload/response OpenAPI schemas, cycle-conflict mapping, and a generic-update guard for `shared:ArchiveUnit` structure fields; added four focused endpoint tests and regenerated-client-compatible contract metadata.
- Open: Publish and deploy the `oldaplib` build containing `ArchiveTree`, then raise the API dependency floor in the release that consumes it.
- Risks/Assumptions: The optional import keeps the API bootable with the currently locked `oldaplib` 0.7.2 but returns `503` for archive moves until that dependency is upgraded. Focused tests pass with the sibling library on `PYTHONPATH`; the pre-existing broad formatting baseline in `instance_views.py` was not rewritten.

### Update 2026-07-23 18:07
- Decisions: Keep browser and native authentication failure semantics aligned for backend transport outages without changing token, cookie, or media capability contracts.
- Implementation: Browser login, refresh, and logout now map `requests.RequestException` to cache-safe `503` responses; logout still clears the refresh cookie. Added focused regressions for all three paths.
- Open: Production deployment still requires a refresh-capable `oldap-app` image (`v0.2.4+`) and coordinated API/media cutover; login/refresh abuse controls remain operational work.
- Risks/Assumptions: Transport exceptions are treated as service unavailability, while invalid credentials and token failures retain their existing status codes.

### Update 2026-07-22 16:16
- Decisions: Harden only the additive mobile authentication transport and existing password-reset key validation; preserve browser routes, Variant D token semantics, oldaplib, media/IIIF capabilities, and stateless refresh behaviour.
- Implementation: Mobile login now rejects passwords above bcrypt's 72-byte UTF-8 limit, mobile `401` responses emit a Bearer challenge, and GraphDB transport failures return stable cache-safe JSON `503` responses. Added dedicated OpenAPI mobile-error responses, enforced password-reset signing-key separation, corrected repository guidance, and expanded regressions for invalid and oversized credentials, expired/inactive/permission-revoked refresh tokens, media/access token confusion, backend outage, and key reuse. All 30 focused authentication, boundary, and password-reset tests pass; Black, OpenAPI, lock, dependency, and diff checks pass.
- Open: Deployment must expose `/mobile/v1/auth/*` over TLS, configure exact CORS origins when WebView fetch is used, and provide login/refresh abuse controls.
- Risks/Assumptions: Variant D intentionally retains fixed-lifetime bearer refresh tokens, local-only normal logout, global `authVersion` revocation, and access-token validity until short expiry; the full repository test suite was not rerun because this review was limited to the authorized authentication scope.

### Update 2026-07-21 17:52
- Decisions: Add a cookie-free native transport for the existing Variant D token model without changing oldaplib, browser authentication, token claims, media/IIIF capabilities, refresh rotation semantics, or logout behaviour.
- Implementation: Added `/mobile/v1/auth/login` and `/mobile/v1/auth/refresh`, strict JSON token responses with no-store caching, stable mobile error codes, OpenAPI schemas, and regression tests for cookie absence, stateless refresh reuse, validation, token-purpose confusion, and global `authVersion` revocation. The 15 focused authentication tests, 5 authentication-boundary tests, Black checks for changed auth/test modules, and OpenAPI validation pass.
- Open: Fasnacht Capture must integrate the response-body contract with native Keychain/Keystore storage and client-side single-flight refresh; deployment must expose `/mobile/v1/auth/*` and align its CORS policy with the selected client transport.
- Risks/Assumptions: Refresh JWTs remain bearer credentials with a fixed absolute lifetime and global per-user `authVersion` revocation; the mobile endpoints must be protected by TLS and deployment-level login/refresh abuse controls.

### Update 2026-07-20 17:39
- Decisions: Let `bump-my-version` own all version-file updates so package metadata and the unprefixed runtime SemVer are changed atomically in the generated release commit; reserve the `v` prefix for Git tags and formatted API output.
- Implementation: Registered `oldap_api/version.py` in the bump configuration, made `make-version` read Poetry's package version, and removed the stale post-bump Makefile writes from all patch, minor, and major bump targets.
- Open: Manually align the currently stale runtime version from `v0.2.8` to `0.2.9` before the next bump.
- Risks/Assumptions: Future bump commands require `version.py` to match the configured current version; the health endpoint already adds the `v` display prefix itself.

### Update 2026-07-15 22:32
- Decisions: Document local authentication setup around the ignored `.env.local` workflow without publishing reusable credentials or signing keys.
- Implementation: Added `README.md` guidance under `Testing with "make run"` for generating four distinct JWT secrets, configuring OLDAP service credentials, retaining HTTP-only development cookie settings, checking local dependencies, and starting the API.
- Open: Developers must supply credentials for an active administrator in their own local OLDAP dataset; no credential value is distributed by the repository.
- Risks/Assumptions: The documented `Secure=false` cookie setting is strictly for local HTTP development, and changing generated secrets invalidates previously issued local tokens.

### Update 2026-07-15 17:56
- Decisions: Issue asset/IIIF query capabilities with a dedicated media-token purpose and signing key instead of reusing the API access-token key.
- Implementation: Added `OLDAP_MEDIA_JWT_SECRET` to local/test configuration, raised the declared `oldaplib` minimum to 0.6.20, updated MediaObject lookup verification and OpenAPI descriptions, and documented that the corresponding media deployment key must match while remaining distinct from the upload access key.
- Open: Production must deploy the same newly generated media key to the API and media stack before media capability URLs are exercised.
- Risks/Assumptions: Media capability tokens are short-lived bearer URLs and therefore authorize anyone who obtains the complete URL until expiry.

### Update 2026-07-15 17:34
- Decisions: Keep production authentication values outside Git and let Flask remain the sole exact-origin credentialed CORS authority; retain the documented `Secure`, `HttpOnly`, `SameSite=Lax`, `/admin/auth` refresh-cookie contract.
- Implementation: Extended OpenAPI cookie lifecycle documentation, removed local Makefile credential/signing-key literals, added ignored `.env.local` loading with a non-secret example, and aligned local Docker Redis addressing. Coordinated full environment propagation and deployment validation in `oldap-setup`.
- Open: Browser integration is work package 6; production password-reset mail still requires an explicit SMTP backend/configuration if console delivery is not intended.
- Risks/Assumptions: Local run targets now require a populated `.env.local`; test fixtures continue to use explicit non-production credentials and keys under test isolation.

### Update 2026-07-15 17:18
- Decisions: Complete authentication work package 4 with one explicit decorator rather than a global request hook; preserve domain-level `403` permission responses while making all Bearer credential failures a uniform `401`.
- Implementation: Added `oldap_api.authentication.require_auth`, strict Bearer parsing, one request-scoped authenticated `Connection`, cache-safe challenges, and operational `503` handling. Migrated all protected user, project, role, resource, hierarchical-list, datamodel, and instance routes; removed their local header splitting; updated invalid-token regressions and the OpenAPI unauthorized response; added a route-registry enforcement test.
- Open: Work package 5 must complete production environment/deployment wiring and operational validation; browser integration remains work package 6.
- Risks/Assumptions: `401` intentionally replaces legacy invalid-token `403` behavior; authorization failures after successful authentication remain endpoint-specific `403` responses.

### Update 2026-07-14 23:41
- Decisions: Implement stateless normal requests with an absolute-lifetime HttpOnly refresh cookie and one persisted per-user `authVersion`; use explicit authentication service credentials for fresh user lookup/revocation, exact optional origin allowlisting, and retain the legacy DELETE logout route only as a delegating compatibility path.
- Implementation: Login now returns `accessToken`, Bearer metadata, expiry, and the transitional `token` alias while setting a purpose-specific refresh cookie. Added refresh and global logout endpoints, cookie/no-store helpers, fresh permission loading, version checks, origin validation, credential-aware CORS, strict password-reset JWT purpose/audience validation, OpenAPI contracts, new environment wiring examples, and GraphDB-backed endpoint tests.
- Open: Work package 4 must replace duplicated bearer parsing in protected views with one authentication boundary; production deployment still needs the new access/refresh/reset secrets and `OLDAP_AUTH_ADMIN_USER/PASSWORD` wiring.
- Risks/Assumptions: Logout is intentionally global across devices, access tokens remain usable for at most their configured short lifetime, refresh tokens are not rotated, and cross-origin cookies require an exact `OLDAP_AUTH_ALLOWED_ORIGINS` list.

### Update 2026-06-18 23:31
- Decisions: Treat datamodel resource response order as non-contractual in tests because `hyha:HyhaUser` can coexist with `hyha:Sheep` in the same test datamodel.
- Implementation: Updated create/delete/modify datamodel tests to select the asserted resource by IRI instead of assuming `resources[0]` is `hyha:Sheep`; tightened `testproject` fixtures so stale datamodel graphs are deleted before and after project tests.
- Open: None.
- Risks/Assumptions: API behavior was left unchanged; focused verification covered the ten reported failures and the three touched datamodel test modules.

### Update 2026-06-18 23:05
- Decisions: Expose oldaplib's one-hop `LinkedResourceSearchFilter` through the existing structured instance-search `filter` array instead of adding a new top-level request field.
- Implementation: Added parser support for linked filters with `linkProperty`/`linkProp`, optional `linkedClass`/`linkClass`, direct comparison fields, and `checkLinkedPermissions`; updated OpenAPI `SearchFilterItem`, `doc/search_instance.md`, parser tests, and project context.
- Open: Regenerate downstream clients from `API-def/oldap-api.yaml`; deploy with an oldaplib build that includes `LinkedResourceSearchFilter`.
- Risks/Assumptions: Linked-resource filters intentionally support only one hop and only work in POST structured search requests, matching the existing behavior for complex filter arrays.

### Update 2026-06-15 23:34
- Decisions: Implement password reset in `oldap-api` as generic OLDAP user infrastructure with one-time JWT reset links bound to `oldap:passwordResetRequestAt`; keep mail delivery configurable and default it to console logging for development.
- Implementation: Added `/admin/auth/password-reset/request` and `/admin/auth/password-reset/confirm`, SMTP/console reset-mail helpers, OpenAPI request/response schemas, and regression tests for request, email lookup, superseded token rejection, successful reset, non-unique lookup, and expired tokens.
- Open: Wire the FasnachtsPage frontend dialogs to the new endpoints and configure production SMTP/frontend URL environment variables.
- Risks/Assumptions: Requires deployed `oldaplib` support for `User.passwordResetRequestAt`, `UserAttr.PASSWORD_RESET_REQUEST_AT`, and `User.search(email=...)`; reset-mail sender identity and wording may need production tuning.

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
