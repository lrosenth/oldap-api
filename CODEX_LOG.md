# CODEX_LOG

### Update 2026-08-09 10:30
- Decisions: Distinguish a restored legacy StagingArea without `shared:stagingQuotaBytes` from a missing or unauthorized target; retain fail-closed target and permission checks.
- Implementation: Made quota projection optional in the target authorization query so the existing domain check returns `503 IMPORT_QUOTA_NOT_CONFIGURED`. Added query and behavior regression coverage for a valid target with no quota.
- Open: None for this diagnostic correction.
- Risks/Assumptions: A missing/invalid target or insufficient effective DATA_UPDATE remains intentionally indistinguishable as `IMPORT_TARGET_NOT_FOUND`; only a target that otherwise passes authorization can disclose its missing quota.

### Update 2026-08-09 00:00
- Decisions: Extend the generic class-transform contract with one optional source relation instead of adding a Fasnacht-specific endpoint. Require shape/range validation and a transaction-time `DATA_UPDATE` check on the source.
- Implementation: Added the closed `linkFrom { resourceIri, property }` HTTP payload, strict validation, oldaplib forwarding, OpenAPI/Zod contract support, and focused endpoint tests. The relation and class transformation now commit or roll back together in oldaplib.
- Open: Publish the accompanying oldaplib release, update this repository's Poetry lock to that version, and run the authenticated Staging-to-Archive browser workflow before deployment.
- Risks/Assumptions: The source and transformed resource belong to the same OLDAP project data graph. Existing callers that omit `linkFrom` retain unchanged behavior.

### Update 2026-08-07 12:53
- Decisions: Persist imported `oldap:Thing` audit timestamps with the ontology-required `xsd:dateTimeStamp`; do not loosen oldaplib conversion or add a special Staging update path to tolerate incorrectly typed RDF.
- Implementation: Corrected the atomic ZIP-import resource insert from `xsd:dateTime` to `xsd:dateTimeStamp` and added transaction-query regression assertions. Repaired the local pilot's 226 affected creation/modification triples across 113 imported Staging folders/media without changing their lexical timestamps or other metadata.
- Open: Restart oldap-api before another ZIP import. Continue exercising Trash restore/permanent deletion and Staging-to-Archive transformation in the pilot UI.
- Risks/Assumptions: The repair selected only `shared:StagingFolder`/`shared:StagingMediaObject` audit values whose datatype was exactly `xsd:dateTime`; the post-repair count is zero. The originally failing authenticated move-to-Trash request now returns HTTP 200 with the correct CORS origin. Five focused commit tests and formatting pass.

### Update 2026-08-07 11:52
- Decisions: Give ZIP-imported media the same canonical delivery metadata as normal media-server uploads. Derive the public IIIF/media bases from the already authoritative `OLDAP_MEDIA_INGEST_URL`; do not persist an internal worker address or let the browser infer a relative URL.
- Implementation: Added `shared:serverUrl` to every atomic staging-media insert (`<media-base>/iiif/3/` for images and `<media-base>/` for HTTP assets), with an injectable repository base URL and transaction regression coverage.
- Open: Restart oldap-api before the next ZIP import. Existing imported resources without `shared:serverUrl` are handled by the accompanying FasnachtsPage compatibility fallback.
- Risks/Assumptions: `OLDAP_MEDIA_INGEST_URL` is browser-reachable because the API already returns it as the direct SIP upload capability base. Seven focused repository/commit tests pass; Black and whitespace checks pass.

### Update 2026-08-07 11:31
- Decisions: Keep the final ZIP-import authorization strict and transactional, but match the canonical RDF datatype used by the OLDAP admin model rather than weakening the check or bypassing reauthorization.
- Implementation: Changed the commit-time project short-name literal from an untyped/string literal to `xsd:NCName`, fixing false `ADMIN_CREATE` rejection after a valid ZIP was confirmed. Added a focused regression test for the generated authorization query.
- Open: Restart oldap-api and submit a new ZIP import; the already failed import cannot be resumed because media correctly compensated promoted assets and deleted its temporary payload.
- Risks/Assumptions: OLDAP project short names are canonically stored as `xsd:NCName`, as enforced by the project model. All five focused atomic import-commit tests pass.

### Update 2026-08-07 00:30
- Decisions: Keep ZIP import project-neutral by resolving each OLDAP project's absolute data-graph IRI from `namespaceIri`; do not repair undefined QNames with a hard-coded project prefix. Recognize asserted project-specific StagingArea subclasses explicitly rather than depending on GraphDB reasoning.
- Implementation: Replaced every dynamic `project:data` reference across create authorization, validation preflight, commit reauthorization, collision checks, and atomic resource insertion with the resolved absolute graph IRI. Corrected all import SPARQL from the obsolete HTTP Schema.org namespace to the ontology's HTTPS namespace, added subclass-path checks, and added regression coverage for the real OLDAP UUID targets and absolute Fasnacht data graph.
- Open: Restart oldap-api and retry after reauthentication. The local `BMG-Archivist` role currently has only `DATA_VIEW` on the selected StagingArea and must be deliberately raised to at least `DATA_UPDATE` before the import authorization can pass.
- Risks/Assumptions: OLDAP project namespaces are stable and form their conventional data graph by appending `data`. Graph resolution occurs before the atomic import transaction; project namespace changes are not a supported concurrent operation. All 53 focused import/authentication tests, Black, and whitespace checks pass; the corrected target-preflight query succeeds against the real local Fasnacht graph and UUID resources.

### Update 2026-08-06 16:02
- Decisions: Align the public ZIP-import target boundary with OLDAP's real resource identity model: allow HTTP(S) IRIs and canonical `urn:uuid` identifiers, while continuing to reject all other URI schemes.
- Implementation: Corrected create-request IRI validation and added an HTTP regression proving real StagingArea/StagingFolder UUID URNs are accepted plus rejection coverage for malformed UUID URNs, generic URNs, `file`, `data`, and `javascript` schemes.
- Open: Restart the local API and repeat the browser ZIP-import request; subsequent authorization and quota checks remain authoritative.
- Risks/Assumptions: UUID URNs are accepted only in lowercase canonical hyphenated form, matching OLDAP-generated instance IRIs. The OpenAPI `format: uri` contract already covered URNs and required no change. All 52 focused import/authentication tests, Black, and whitespace checks pass.

### Update 2026-08-05 23:25
- Decisions: Use the oldap-mediaserver ZIP-import operations runbook as the cross-service authority for API, GraphDB, media, and frontend operations. Do not delete API lifecycle records independently from retained media reports/manifests.
- Implementation: Synchronized stable API context with the completed deployment, backup, retention, incident-response, and recovery runbook and its pre-pilot checklist; no API runtime code changed.
- Open: Implement or explicitly accept safe paired 30-/90-day record pruning; confirm university backup/RTO, Defender, and logging details; add durable feature gating and complete deployed pilots.
- Risks/Assumptions: Temporary payload retention is automated, but terminal API jobs and corresponding media records currently remain indefinitely until coordinated pruning exists.

### Update 2026-08-05 23:12
- Decisions: Close the Phase 6 automated lifecycle matrix with focused domain/filesystem/contract tests instead of introducing a second integration harness. Keep production-size, destructive mount-pressure, real process-kill, backup/restore, and authenticated deployed-browser exercises operator-only.
- Implementation: Added a complete create-to-IMPORTED-plus-cleanup service lifecycle test with retained audit events and quota assertions; added synchronized global-claim and READY-confirmation race tests. The cross-repository matrix now maps these to media crash/retry/cleanup and frontend lifecycle evidence.
- Open: Complete deployment/backup/retention/incident/recovery runbooks, feature gating, and test/production pilots.
- Risks/Assumptions: The happy-path lifecycle test uses the thread-safe reference repository; GraphDB transaction shape and atomic commit remain covered separately. All 51 focused import/authentication tests pass; Black and whitespace checks pass.

### Update 2026-08-05 22:47
- Decisions: Reconcile import email inside oldap-api, never in media. Use the existing single worker's idle claim polls as a trigger, attempt at most one due job per poll, cap submissions at three, and require five minutes after a failed attempt. Do not delay a newly leased ingest task for SMTP.
- Implementation: Persisted notificationLastAttemptAt, added deterministic oldest-first retry selection for PENDING/FAILED notifications, reset retry timing for each new lifecycle email, and added non-blocking idle-poll reconciliation. Added backoff/bound/trigger tests and synchronized the cross-repository reconciliation plan.
- Open: Implement physical disk admission, structured owner-visible operations, runbooks, feature gating, and authenticated pilots.
- Risks/Assumptions: Delivery is bounded at-least-once because SMTP acceptance can be ambiguous if API persistence fails afterward. A single sequential ingest worker is the MVP trigger source; multiple independent workers would require a separate atomic mail lease. Fifty focused import/authentication tests pass; formatting, compilation, and whitespace checks pass.

### Update 2026-08-05 22:40
- Decisions: Make API state/deadlines the sole authority for finalized ZIP cleanup. Select CLEANUP on the existing global lease queue; finalize EXPIRED only after media deletion proof; preserve IMPORTED extracted-byte quota; explicitly exclude IMPORTING and unexpected intermediate states.
- Implementation: Added 24-hour UPLOADING and persisted READY-expiry eligibility, idempotent cleanup result persistence/endpoint, active-claim/version/reason validation, EXPIRED transition and terminal cleanupPending clearing, upload-capability/late-callback race guards, OpenAPI schemas, HTTP/domain/replay tests, and synchronized documentation.
- Open: Add reconciliation for orphaned work/final assets, pending callbacks/email, disk admission, operations/runbooks, and pilot rollout.
- Risks/Assumptions: A deleted payload with an unavailable API is safe to retry after lease expiry because deletion is idempotent and the API job remains unchanged until proof is accepted. Forty-eight focused import/authentication tests pass; compilation, YAML parsing, formatting, and whitespace checks pass.

### Update 2026-08-05 22:24
- Decisions: Mark ZIP-import Phase 5 complete now that FasnachtsPage uses the existing optimistic confirmation boundary and follows both successful and compensated terminal import outcomes. Keep lifecycle cleanup and operational activation in Phase 6.
- Implementation: Synchronized stable API context with the completed cross-repository confirmation/import workflow; no API runtime code changed in this closure step.
- Open: Implement API-claimed READY/UPLOADING/success cleanup, reconciliation, disk admission, and pilot operations in Phase 6.
- Risks/Assumptions: The browser action remains advisory; oldap-api is authoritative for stateVersion, permissions, target integrity, quota, and collisions at confirmation/commit.

### Update 2026-08-05 22:06
- Decisions: Accept terminal IMPORT failure only after the media worker proves both job-owned asset compensation and temporary-payload deletion. Keep this result idempotent and independent from the successful staging batch.
- Implementation: Added retained task-failure event/digest state, strict IMPORT-only compensated/deleted validation, active-claim/version checks, atomic IMPORTING -> FAILED with quota release, exact replay, notification handoff, internal endpoint, and authoritative OpenAPI contract. The media worker now retains and replays matching failure evidence after API outages.
- Open: Complete the FasnachtsPage confirmation/user-flow slice; successful temporary-payload cleanup remains Phase 6.
- Risks/Assumptions: `IMPORT_COMMIT_REJECTED` intentionally summarizes the internal API rejection without persisting sensitive response bodies. Ambiguous commit responses do not use this endpoint because the resource transaction may have succeeded.
- Verification: All 42 focused import/authentication tests pass; both authoritative OpenAPI contracts validate; compilation and whitespace checks pass.

### Update 2026-08-05 21:53
- Decisions: Implement the confirmed import as one API-owned GraphDB transaction rather than per-resource oldaplib creates. Reauthorize the original user from live GraphDB facts, inherit the staging area's default role/permission, derive resource IRIs with UUIDv5 from import/path, and identify replay mappings by relative path so implicit ZIP parent folders can share a descendant source index. Keep detailed codec/probe evidence in the retained immutable manifest instead of widening the closed StagingMediaObject ontology in the MVP.
- Implementation: Added the closed folder/media commit validator, deterministic asset/IRI and delivery-fact checks, retained import event/digest/resource mappings, active-lease and manifest binding, exact replay, fresh target/ADMIN_CREATE/DATA_UPDATE/default-role/collision checks, complete StagingFolder/StagingMediaObject SPARQL insertion, and atomic IMPORTED job replacement. Added the internal commit endpoint, notification handoff, authoritative OpenAPI schemas, and focused service/HTTP/transaction tests; synchronized the standalone cross-service contract.
- Open: Wire the media IMPORT worker to synthesize implicit folders, prepare/promote assets, call this endpoint, compensate failed commits, and publish terminal failures. Cleanup of successful temporary payloads remains Phase 6.
- Risks/Assumptions: Production relies on GraphDB transaction isolation and RDF-star support already required by OLDAP. Same-name media siblings at the selected existing root remain allowed by decision D-004; folder-involving collisions block. Atomic insert uses closed facts matching the shared staging/media shapes rather than invoking per-resource oldaplib transactions.
- Verification: Forty-one focused import/authentication tests pass; both authoritative OpenAPI documents validate; compilation and whitespace checks pass.

### Update 2026-08-05 11:55
- Decisions: Keep current staging hierarchy inspection inside oldap-api; expose a strict claim-bound preflight rather than GraphDB credentials or broad query results to media. Folder/type conflicts block, media/media name equivalence warns, and Phase 5 must recheck races during commit.
- Implementation: Added the bounded OldapImportTargetInspector for direct shared:inStagingFolder children, VALIDATE lease/version/worker validation, NFC/portable collision projection, the internal target-preflight route, authoritative OpenAPI schemas, and focused route/query tests.
- Open: Phase 4 still needs media total-deadline/FAILED handling and parser isolation. Phase 5 must reauthorize and repeat target/collision checks in the atomic staging-resource commit.
- Risks/Assumptions: Inspection deliberately fails operationally above 10,000 direct children rather than returning incomplete evidence. shared:originalName is authoritative for media collision warnings with schema:name as fallback. All 29 focused import tests and the main OpenAPI validation pass.

### Update 2026-08-05 03:10
- Decisions: Make a leased VALIDATE claim self-contained for immutable manifest generation rather than letting the media worker invent job facts or perform a user-authorized lookup.
- Implementation: Extended ImportClaim and both authoritative OpenAPI contracts with jobCreatedAt, requestedByIri, originalFileName, and compressedSizeBytes; populated them from the canonical ImportJob and added endpoint assertions.
- Open: Content validation and target-child preflight remain media/Phase 4 work; import and cleanup claims reuse the additive facts.
- Risks/Assumptions: compressedSizeBytes uses the accepted SIP receipt when available and the declared size only before receipt. Twenty-five focused ZIP-import API tests and the main OpenAPI validation pass.

### Update 2026-08-05 00:30
- Decisions: Close ZIP import Phase 2 at the API ownership boundary. Keep list cursors opaque and tied to an exact owner/filter result set; use a strict audit-log whitelist instead of logging serialized jobs or request bodies. Import/cleanup completion events remain in the later execution phases.
- Implementation: Added deterministic newest-first cursor pagination and its authoritative OpenAPI contract; rejected unknown list parameters and invalid/stale cursors. Added privacy-preserving lifecycle audit events with sanitized request IDs and no filenames, tokens, claim IDs, checksums, targets, or report content. Added expiry, concurrent quota-race, pagination, malformed-input, and log-redaction tests.
- Open: Phase 3 must implement media-owned immutable SIP ingress/quarantine, upload-capability verification, and the durable SIP-stored callback. Existing staging areas require positive `shared:stagingQuotaBytes` before rollout.
- Risks/Assumptions: GraphDB transaction isolation remains the production cross-process quota authority; the synchronized in-memory race test proves repository semantics but deployment verification must exercise the configured GraphDB transaction mode. Thirty-three focused import/password-mail tests and eight authentication-boundary tests pass; Black, compilation, OpenAPI validation, and whitespace checks pass.

### Update 2026-08-05 00:18
- Decisions: Keep report bytes on media and proxy only after API ownership authorization plus exact retained SHA-256 verification; use a seventh purpose-specific import-records JWT key. Keep notification submission state independent from lifecycle state and accept bounded at-least-once SMTP semantics rather than pretending email can be transactional.
- Implementation: Added protected report retrieval, five-minute API-to-media records tokens, response size/time/checksum/identity/outcome checks, and private no-store responses. Extracted shared console/STARTTLS mail transport from password reset; added token-free READY/INVALID/FAILED/IMPORTED content and PENDING/SENT/FAILED status with at most three attempts. Validation commits precede mail submission and SMTP failures record only exception class without lifecycle rollback.
- Open: Media must implement the internal retained-record endpoint in Phase 3/4. Phase 2 still needs import commit/failure, cleanup completion, and final audit/log coverage.
- Risks/Assumptions: SMTP is necessarily at-least-once across a crash between relay acceptance and status persistence, so a rare duplicate message is preferable to lost authoritative state. Twenty-four focused tests pass; live SMTP and media-record integration remain deployment tests.

### Update 2026-08-04 23:58
- Decisions: Implement the lean queue as one API-selected global lease rather than a broker; increment stateVersion when a task is claimed/reclaimed, but keep heartbeat renewal outside lifecycle versioning. Treat the validation summary's extracted bytes as the quota reconciliation authority only when they are consistent with the stored SIP and original reservation.
- Implementation: Added persisted claim metadata, atomic VALIDATE/IMPORT/CLEANUP selection, active-lease exclusion, expired-lease reclaim, worker/version-bound heartbeat, and idempotent READY/INVALID/FAILED validation results. READY requires complete error-free inventory and receives seven-day expiry; INVALID/FAILED require deleted payload and release quota. Added internal endpoints, closed validation, authoritative OpenAPI schemas, and focused lifecycle/replay tests.
- Open: Add report proxying, notification submission state/mail transport extraction, import commit/failure, and cleanup completion events.
- Risks/Assumptions: GraphDB transactions remain the cross-process claim serialization authority. Heartbeats cannot resurrect expired claims. The media worker must submit truthful immutable retained-record hashes; report/manifest retrieval verification follows in the next slice. Seventeen focused import/authentication/repository tests pass.

### Update 2026-08-04 23:46
- Decisions: Separate internal import-service authentication from OLDAP access, media, upload, refresh, and reset tokens; bind the first durable media receipt to the immutable declared ZIP size and accept only exact event replay.
- Implementation: Added `typ=import-service`/`aud=oldap-api-import-service` JWT validation, a dedicated non-token-issuing OLDAP service connection, persisted SIP receipt facts, concurrency-safe idempotent `POST /internal/imports/{id}/sip-stored`, and `UPLOADING -> VALIDATING`. Updated environment examples and the authoritative OpenAPI contract.
- Open: Add worker claims/leases, validation-result events with actual extracted-size quota reconciliation, report proxying, and import notification delivery state.
- Risks/Assumptions: Deployment must exclude `/internal/*` from public proxy routing, configure a distinct Vault-managed service JWT key and service user, and migrate staging-area quotas before enabling job creation. Twelve focused API tests and OpenAPI validation pass.

### Update 2026-08-04 23:18
- Decisions: Persist project-neutral ZIP ImportJobs in the existing GraphDB rather than Redis or a new database; keep canonical job state behind a repository boundary and enforce state versions plus staging-area quota sums in the same transaction as writes. Use a fifth, purpose-specific JWT key for direct SIP upload capabilities.
- Implementation: Added immutable ImportJob lifecycle/value types, conservative quota reservation, in-memory and GraphDB repositories, OLDAP ADMIN_CREATE/DATA_UPDATE target authorization, scoped upload capability issuance, and authenticated create/list/read/reissue/cancel/confirm endpoints. Registered the blueprint, documented the public OpenAPI contract and runtime settings, and declared the direct RDFLib dependency.
- Open: Phase 2 remains in progress: add `shared:stagingQuotaBytes` to shared ontology/SHACL, internal service-token authentication, SIP/validation result idempotency, worker claims/leases, actual-size quota reconciliation, report proxying, and reusable import mail notifications.
- Risks/Assumptions: The public create/confirm paths intentionally fail closed until staging areas expose a positive `shared:stagingQuotaBytes`; GraphDB transaction isolation is the concurrency authority. Nine focused domain/HTTP/authentication-boundary tests pass; live GraphDB integration and full-suite verification remain to be completed.

### Update 2026-08-04 15:23
- Decisions: Make password-reset links independent of mail-client plain-text URL detection while retaining a readable fallback for non-HTML clients.
- Implementation: Percent-encoded JWT segment separators in reset URLs and changed SMTP delivery to UTF-8 multipart mail with a complete plain-text link, HTML reset button, copyable fallback URL, proper German characters, and focused MIME/link round-trip tests.
- Open: Build and deploy the updated API image, request a fresh reset message, click the HTML button, and complete one password change without manually copying the URL.
- Risks/Assumptions: The frontend continues to use standard URL query decoding, which restores `%2E` to JWT dots before submitting the token; previously issued tokens and links are unaffected.

### Update 2026-08-04 14:56
- Decisions: Diagnose production SMTP from inside the API container using the same mail environment variables, while keeping passwords out of command arguments, process listings, and terminal output.
- Implementation: Added the interactive/non-interactive `python -m oldap_api.smtp_test` utility with STARTTLS, implicit TLS, plain SMTP, authentication, certificate validation, timeout, and delivery-submission diagnostics; documented container usage and added focused unit tests.
- Open: Run the diagnostic on the production host, configure the confirmed SMTP values, and set `OLDAP_PASSWORD_RESET_FRONTEND_URL=https://fasnacht.digital`; implicit TLS findings would require extending the API mailer before deployment.
- Risks/Assumptions: SMTP acceptance does not guarantee inbox placement; final delivery and spam handling must be checked at the recipient mailbox.

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
