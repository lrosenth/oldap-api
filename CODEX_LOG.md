### Update 2026-11-14 19:29
- Decisions: Completed owner-authorized coordinated 1.2.0 release and home.org rollout; production unchanged.
- Implementation: All three main branches and v1.2.0 tags pushed; library wheel/sdist published and hash-verified. API/tools locks update only oldaplib. Published accepted AMD64/ARM64 images; installed home API/identity and tools selection. Added/read back nine ontology triples with before-graph and exact rollback.
- Open: No requested release/deployment work remains. Future home deployments must use releases/home-1.2.0.json; other direct-library writers require compatibility before annotated-data use.
- Risks/Assumptions: 99 installed regressions per architecture plus packaged Jena and tools checks pass. Public home health/status/Fasnacht pass; six sibling container IDs unchanged. No live business-data write acceptance; retain ontology/data on image rollback. See release-1.2.0.md and receipt.

### Update 2026-11-14 19:14
- Decisions: Owner authorized merging all three reification branches, coordinated 1.2.0 publication and home.org deployment including additive OLDAP ontology update.
- Implementation: Fast-forwarded main to reviewed feature commits; bumped package versions to 1.2.0. API/tools require oldaplib >=1.2.0,<2.0.0; exact library pins will be frozen in images.
- Open: Package publication, consumer locks, installed image acceptance, registry publication and home deployment verification.
- Risks/Assumptions: Production is outside scope. Preserve unrelated setup changes, existing registry tags and business data; retain ontology/image rollback evidence.

### Update 2026-11-14 18:53
- Decisions: Completed explicitly requested final-check across all four stages and three repositories; two full review passes. Ready for coordinated local source merge; no merge performed.
- Implementation: Corrected model-cache overhead/transaction completion eviction, graph and nested-node ownership, model attachment guards, copy notifications, legacy dialect, scalar comparisons, permission revocation, protected fields, API errors/hierarchy restore and OpenAPI quoting. Updated tests and current cache/profile documentation; see oldaplib/docs/reification-final-check.md (relative to OLDAP workspace).
- Open: Coordinated release versions, installed-artifact and live HTTP/Redis/GraphDB/platform acceptance remain separate. No unresolved source findings.
- Risks/Assumptions: Combined isolated suite 366 passed plus 9 subtests; three opt-in checks passed separately. Three wheels built; full OpenAPI validation passed. No measured warm-path regression, with transport/cold-cache/production limits documented. No commits, push, merge or live changes.

### Update 2026-11-14 18:41
- Decisions: Explicit final-check workflow covers all four stages across all three repositories. First audit completed before fixes; see oldaplib/docs/reification-final-check.md.
- Implementation: Starting collective corrections for cache/read overhead, graph/nested ownership, model attachment guards, copy tracking, legacy dialect, scalar comparison and API restore/error boundaries.
- Open: Regression verification, second complete review, package/schema checks and final readiness conclusion.
- Risks/Assumptions: No live test targets, service changes, commits, push or merge; existing source-matched local environment used.

### Update 2026-11-14 01:41
- Decisions: Accept stage 4 locally: explicit conjunctive same-reifier filters, same-value field ranges, asserted-base absence semantics and opt-in complete page projection. Ordinary read/search query paths remain unchanged.
- Implementation: Added typed/compiler module, reusable fresh policy resolution, strict POST API parsing/OpenAPI and native ACL/graph/paging regressions. Corrected three pre-existing query-text expectations for SPARQL terminators. Acceptance: 11 stage-4 tests, 18 stage-3 tests, 122 focused library/API tests/two subtests. Stored paired source-hashed timing, optimized native algebra and reconstructible stage-3 baseline patch; no measured ordinary-path slowdown.
- Open: Separate coordinated release/live acceptance; annotation sorting/fulltext/aggregation deferred. No tools search grammar needed.
- Risks/Assumptions: New annotated searches pay explicit model-resolution cost; page annotation projection adds parent/record reads. Local timings do not establish production capacity. No commits, publication, live model changes or deployment.

### Update 2026-11-14 01:30
- Decisions: Stage 4 adds explicit conjunctive annotation-filter groups and opt-in page projection. Default reads/searches must retain query text/count and results.
- Implementation: Starting model-resolved correlated EXISTS compilation and REST parsing; shared reifier field bindings prevent cross-visit matches.
- Open: Native semantics/ACL/paging regressions, API documentation and comparative performance acceptance.
- Risks/Assumptions: Local RDF 1.2 backend only; annotation sorting/fulltext/aggregation remain out of scope.

### Update 2026-11-14 01:25
- Decisions: Accept stage 3 locally; annotation loading is explicit and ordinary reads/searches retain exact query text/count. OLDAP remains the validator; stage 4 search is next.
- Implementation: Completed managed annotation lifecycle, typed JSON, parent ACL/ownership checks, transactional cleanup, history restore/no-ops and API documentation. Added native cross-graph/shared identity and self-link deletion regressions. Acceptance: 18 native tests, 100 focused library/API tests, 200 tools tests/seven subtests; source-hashed paired performance receipt resolves no slowdown.
- Open: Stage 4 filters/projection; separate artifact release and live HTTP/Redis acceptance. Instance-data YAML and annotated class transformations explicitly reject unsupported operations.
- Risks/Assumptions: Pinned isolated Jena 6.2.0; local warm timings are not production capacity evidence. External/blank/shared/orphan reifiers remain read-only. No live changes, commits or publication.

### Update 2026-11-14 01:18
- Decisions: Stage 3 uses explicit lazy annotation loading; ordinary reads/searches retain their query text/count. Parent ACLs, fresh policy checks and resource transactions govern writes.
- Implementation: Added identified annotation CRUD, typed RDF-term JSON, history snapshots/restoration and native integration tests. Unsupported annotated transformations and instance-data YAML remain explicitly blocked. Local benchmark compares current sources with pre-stage-3 HEAD on the same Jena dataset.
- Open: Complete edge-case/API regression acceptance, documentation and final performance receipt before closing stage 3.
- Risks/Assumptions: Managed exclusive IRI reifiers only; blank/shared/external/orphan records are read-only. Matching local sources required; no live service changes.

### Update 2026-11-14 00:53
- Decisions: Complete stage 2 locally on codex/reification-properties; preserve omitted definitions and require explicit null plus --remove-unused for shape deletion.
- Implementation: Added reifier fields to existing standalone/scoped property-update allowlists; shape field replacement preserves absent uniqueLang instead of injecting false. Actual tool-driven CRUD, zero/false/clear, replay and backups pass. Acceptance: 199 tools tests/seven subtests and 84 focused library/API tests pass; native cases use pinned Jena 6.2.0 in disposable TDB2 with Python sockets blocked.
- Open: Stage 3 instance annotation CRUD/validation; stage 4 search. Coordinated package release and deployment remain separate.
- Risks/Assumptions: Existing per-request/per-object commits; fresh plans support recovery, not whole-file atomicity. Final in-use/foreign-reference checks remain server-side. Matching sibling development sources required; no live HTTP or Redis acceptance.

### Update 2026-11-14 00:36
- Decisions: Complete stage 1B locally; retain OLDAP validation and gate annotated instance writes until stage 3.
- Implementation: Model API exposes named reifier shape CRUD and property-use attachments with explicit false/clear semantics; legacy annotationProperties remains unchanged. OpenAPI documents the contract. See doc/reification-model.md. Verification: 83 focused tests and seven isolated native Jena checks pass.
- Open: Stage 2 YAML; stage 3 instance lifecycle; stage 4 search; coordinated release remains separate.
- Risks/Assumptions: Draft SHACL profile, conservative in-use checks; no whole-model atomic update or live HTTP/Redis acceptance. No publication/deployment.

### Update 2026-11-11 17:23
- Decisions: Complete authorized 1.1.0 Git/PyPI/Docker release without deploying live services.
- Implementation: Published and hash-verified oldaplib 1.1.0 on PyPI; API/tools multiarch v1.1.0 and harvester 0.1.15 standard/OCR images are published. Retained Jena service 1.1.0 artifact and immutable release receipts.
- Open: Later deployment must include Jena service 1.1.0 for history-aware transfer; frontend remains separate.
- Risks/Assumptions: Focused source and installed-image tests, native transfer/service and packaged Jena integration pass. Existing/latest tags unchanged; no live data writes. See doc/release-1.1.0.md.

### Update 2026-11-11 17:12
- Decisions: Release the property-history read/restore endpoints with oldaplib 1.1.0.
- Implementation: Synchronized API/OpenAPI versions and targeted library lock; all third-party versions retained.
- Open: 133 focused cross-project tests pass; Docker acceptance/publication pending.
- Risks/Assumptions: New history-aware project transfer additionally requires Jena service 1.1.0; no deployment.

### Update 2026-11-11 16:07
- Decisions: Owner-authorized production promotion of the exact home-tested image and ontology patch; Jena/Fuseki only, no additional SHACL or feature-validation campaign.
- Implementation: Activated digest 9064a52835c3cdf4f4963a58c71c32b81ab960c2a87902a726cc2b5e08e8c5a0 (library/API 1.0.1+jena.rc1.f4621e4dee0b). Added 21 history-definition triples under installed batch/recovery locks, preserving the original ontology and additive rollback. Updated setup's current API selection and production evidence.
- Open: Frontend admin integration remains separate. Tools/harvester library pins are unchanged; no new stable package release or Git publication requested.
- Risks/Assumptions: Installed source hashes match home; API/Jena health and Fasnacht HTTP 200 pass. Only API/identity restarted; six other container IDs unchanged. No production business-data write tests. Compose rollback: /opt/oldap/compose/routine-update-20261111T150600672366Z; ontology recovery is documented in setup docs/property-history-production-20261111.md.

### Update 2026-11-11 14:56
- Decisions: Owner-authorized home-only deployment and OLDAP ontology addition; Jena/Fuseki only, no new SHACL validation campaign.
- Implementation: Published/activated library/API candidate 1.0.1+jena.rc1.f4621e4dee0b (multiarch digest 9064a52835c3cdf4f4963a58c71c32b81ab960c2a87902a726cc2b5e08e8c5a0). Added 21 triples across seven history subjects; preserved existing ontology/data. Saved ontology and Compose rollback artifacts; recorded the home-only release selection.
- Open: Frontend admin integration and any stable/production promotion remain separate. Use the explicit home release file to avoid reverting to the previous API. Tools/harvester pins retain their prior libraries.
- Risks/Assumptions: Existing isolated image-publication gate passed on both architectures. Exact installed source hashes and public readiness pass; only API/identity container IDs changed. No home business-data writes, frontend changes or additional SHACL tests. Recovery: setup docs/property-history-home-20261111.md.

### Update 2026-11-11 00:32
- Decisions: Expose property history through two simple endpoints and reuse the complete ordinary update pipeline.
- Implementation: Added GET /data/history/{project}/{instanceIri} and POST .../restore, strict request parsing and paging; shared manual/history update and move handlers retain archive/Staging restrictions, including hierarchy restoration through domain commands.
- Open: Coordinated package release and deployment remain separate; implementation and local acceptance complete.
- Risks/Assumptions: 84 focused tests pass, including executed RDF SPARQL; 12 isolated native Jena checks pass (creation, updates, undo, rollback, Dating, transforms and fulltext exclusion). Ontology/Python parsing and diff checks pass. Legacy GraphDB-dependent transform tests unavailable because localhost:7200 is stopped. Raw SPARQL bypasses automatic history.

### Update 2026-11-10 23:04
- Decisions: Reuse official Apache UI and the native Jena dataset; expose only authenticated loopback console, with same operator credentials as home.
- Implementation: Added optional console lifecycle/readiness, reproducible private installer and regression tests. Installed native Caddy/config/LaunchAgent and accepted same-JVM admin build locally. Repaired stale Poetry interpreter references; existing project environments retained.
- Open: No remote rollout or package release; wider console operations remain subject to existing service ownership constraints.
- Risks/Assumptions: 15 controller/installer tests, native checks (20 HTTPS/22 local), UI byte equality, local query/update/readback/cleanup and real Make stop/status/start pass. Both listeners bind loopback; anonymous/foreign-origin writes denied. Direct console writes bypass API validation by design.

### Update 2026-11-10 15:38
- Decisions: Use a separate verified home snapshot for native Jena development in OLDAP; preserve GraphDB data and configuration for rollback.
- Implementation: Backend-selected service control, private environment runner and independent identity service; ordered drain/start, durable Docker resume IDs and API-only restart. Installed loopback Jena/Redis/API LaunchAgents with fresh backend credentials and editable sibling library. Documented runtime/data provenance and rollback.
- Open: Local upload/import and frontend acceptance; old Jena checkout archival still requires other active-path checks. Snapshot is November 8, not continuous synchronization.
- Risks/Assumptions: 15 focused controller/restart tests pass. Actual stop/status/start and API restart succeed; anonymous/configured login and ten-row archive search pass after restart. Home/production unchanged. Existing local media retained; GraphDB disabled but not deleted.

### Update 2026-11-10 15:22
- Decisions: Reuse the reviewed Jena image pipeline for normal OLDAP development; separate prepare/build/accept/publish from deployment and local native service installation.
- Implementation: Restored docker-prepare, docker-build/docker-image, docker-accept and docker-push through sibling setup. API wheels remain build inputs, with no Python publication. Explicit absolute bundle paths support spaces; legacy docker-run remains labelled as such.
- Open: Local native Jena service configuration and data source; current services controls still target the old GraphDB installation. No publication or remote deployment requested in this step.
- Risks/Assumptions: Candidate builds may resolve newer third-party dependencies unless IMAGE_CONSTRAINTS is supplied; never promote without image acceptance. 43 focused tests and real AMD64/ARM64 image builds plus isolated Jena transaction/persistence/network acceptance pass. See setup docs/image-build-workflow.md.

### Update 2026-11-10 00:22
- Decisions: Owner-authorized Docker publication and production promotion of API/library 1.0.1; preserve existing tags, namespace and other services.
- Implementation: Published accepted AMD64/ARM64 IDs and multiarch digest 7fed616c31b8c298d02778e807bb0713746f0f21cb722662548796d9a573070a. Scoped maintenance-locked rollout replaced API/identity only; saved Compose before-api-1.0.1-20261110T002006. Readiness/auth/media/search checks pass. Browser comparison: text 1845→1500 ms, year 1621→1324, image 1934→1478, detail 2387→2289; three repeats, equal visible content, 231 successful API responses.
- Open: Routine observation and user acceptance; live measurements are small warm samples, not load-test guarantees.
- Risks/Assumptions: No RDF migration, real upload or data-write test in this rollout. Rollback uses retained Compose/images; maintenance lock released. Detailed evidence retained in the 20261110-performance-1.0.1 release directory.

### Update 2026-11-10 00:17
- Decisions: Complete local API 1.0.1 images only; registry publication and deployment remain separate.
- Implementation: Built AMD64/ARM64 from exact 1.0.1 wheels with the accepted Jena recipe/base and retained third-party constraints. Each image passes 61 tests, version/Jena import checks, UID/GID checks and pip check. Recorded image IDs and workflow in doc/performance-release-1.0.1.md; private build logs/manifests retained.
- Open: Live-service acceptance and coordinated Docker publication/deployment.
- Risks/Assumptions: AMD64 tests run under emulation. Focused tests do not replace end-to-end acceptance. Existing deprecation warnings remain; running services unchanged.

### Update 2026-11-10 00:12
- Decisions: Push both mainlines and publish library 1.0.1; owner clarified API distribution should be Docker, not PyPI. API 1.0.1 upload had already completed before clarification; do not repeat for future releases.
- Implementation: make build/publish completed for both packages; library wheel matches the previously locked SHA-256. Targeted poetry update oldaplib adds the published sdist hash only (no third-party lock version changes); local API venv synchronized to the existing lock. Added API make build; removed the newly added publish target following clarification. 61 installed-library tests pass, using copied tests because wheel intentionally excludes oldaplib.test.
- Open: Build API images for AMD64/ARM64 using accepted Jena recipe and retained third-party constraints; no deployment requested.
- Risks/Assumptions: Existing API PyPI artifact remains published. Legacy API Dockerfile is not used for this Jena release. Initial in-tree test collection failed on intentionally absent packaged tests; corrected installed-package run passed.

### Update 2026-11-10 00:08
- Decisions: Merge the accepted performance branch into local main and prepare coordinated patch 1.0.1, as requested. Preserve experiment branches; no push/tag/deployment.
- Implementation: Fast-forwarded main; updated package, runtime and bump metadata plus native service label/OpenAPI version where applicable. API now requires oldaplib >=1.0.1; the existing offline Poetry solver pins its exact local wheel with all third-party versions unchanged. Library lock unchanged. 61 focused tests pass against OLDAP mainline sources.
- Open: Publish/push and deploy in a separate coordinated release. Retained wheel: /Users/rosenth/Library/Application Support/OLDAP-Jena/releases/20261110-performance-1.0.1/wheels/oldaplib-1.0.1-py3-none-any.whl.
- Risks/Assumptions: Unpublished 1.0.1 cannot yet be fetched from the package index; use the retained wheel for local acceptance. Production remains core 1.0.0. Existing dependency deprecation warnings remain.

### Update 2026-11-10 00:02
- Decisions: Owner-requested local checkpoint of the home-accepted performance work on experiment/dating-read-performance; keep it separate from published main until coordinated promotion.
- Implementation: Paired library checkpoint: 43a90ab. Reviewed and retained the focused dating reader, normalized calendar decoding, operation-scoped vocabulary discovery and ACL join changes with tests/profiling evidence. Revalidated 61 focused library/API tests using the API virtualenv and explicit sibling source paths; whitespace checks pass.
- Open: Performance branch merge/push and coordinated API/library production promotion remain separate. Normal OLDAP worktrees are to follow published main; committing this branch does not change main or deployments.
- Risks/Assumptions: Performance candidate 40e6a2f777e3 is deployed on home only; production API/library remain 1.0.0. No runtime changes or package/deployment operation in this checkpoint. The library venv lacks pytest; tests used the existing API venv without installing dependencies. Dependency deprecation warnings remain.

### Update 2026-11-09 22:21
- Decisions: Publish isolated candidate images and verify on home only; keep production/stable tags and namespace owner unchanged.
- Implementation: API/Tools 40e6a2f777e3 accepted on AMD64/ARM64; dependency parity and 29 installed API tests per architecture pass. Home API/identity replaced; 27 live checks, 18 complete response comparisons and desktop/mobile smoke pass. Date medians public 1010 -> 653 ms, admin 2063 -> 786 ms. Setup adds recovery-lock/rollback protection and permits retired GraphDB absence in its checker.
- Open: Home frontend retains duplicate searches; browser median ~2.7 s unchanged within noise. Review frontend alignment and user acceptance before any production rollout. Evidence: ../oldap-setup/docs/archive-performance-home-20261109.md.
- Risks/Assumptions: Candidate snapshots include uncommitted source; no Git/PyPI release. Read-only home checks plus isolated packaged transactions, not live imports/writes. Known taxonomy alias normalized only for semantic comparison; retained rollback environment needs no RDF restore.

### Update 2026-11-09 22:01
- Decisions: Reuse schema graph names only within one read operation; optimize role joins without permission/result caching. Rejected class-placement-only change after neutral measurements.
- Implementation: Bound schema reuse to search plus date expansion. Added three-variant owned benchmark with restored baseline joins, complete responses, native ACL fixtures, counts and nonzero paging comparisons. 103 focused tests pass; native 31 checks plus 270 response comparisons pass. Date search calls 15 -> 10; public/audit date medians 432 -> 367 / 774 -> 426 ms. Sum of nine case medians improves 10% public / 61% audit.
- Open: Coordinated installed-image acceptance and home verification before production. See doc/archive-metadata-optimization.md.
- Risks/Assumptions: Warm sequential local fixture, four samples per variant/case; sums are not page latency. Schema edits during a scoped read appear next operation; transactions bypass reuse. No push, publication or deployment.

### Update 2026-11-09 21:49
- Decisions: Integrate the focused reader and correct calendar decoding independently; preserve public signatures and RDF storage.
- Implementation: Search date expansion now calls the explicit private library reader. Updated sequential baseline comparison and fixtures for subproperties/multiple types/Julian correctness; documented coordinated API/library release requirement. Native run: 24 HTTP comparisons, fixture group and 16 timed comparisons pass; public 551 -> 414 ms, audit 1102 -> 788 ms. Focused tests: 30 passed; broader tests: 13 passed, four failure reports reproduce on original HEAD.
- Open: Joint installed-image acceptance and test deployment before production; older query-string test expectations remain separately unresolved. See doc/dating-read-integration.md.
- Risks/Assumptions: Warm local fixture, sequential timings; no GraphDB live comparison. Calendar correction intentionally changes affected output metadata, not stored dates. No push/publication/deployment.

### Update 2026-11-09 21:18
- Decisions: Measure a focused search-date read before runtime adoption; preserve public contracts and RDF storage.
- Implementation: Added owned sequential query-comparison runner, complete response/ACL/date checks and sanitized results. Public HTTP median 557 -> 390 ms; audit 1129 -> 821 ms; unchanged 15 backend calls. Native run passes 24 HTTP comparisons plus synthetic fixtures and 16 timed equivalence checks; Python tests 8 passed/2 expected failures.
- Open: Explicit private integration and additional property-inheritance/multi-type coverage; separate Julian decoding correction. Evidence: doc/dating-read-experiment.md.
- Risks/Assumptions: Warm local older export, four timing samples per reader/variant; not production or whole-page improvement. Experiment patch is sequential-only. No push/deployment or runtime activation.

### Update 2026-11-09 21:01
- Decisions: Isolate the dating-read performance experiment on local branch `experiment/dating-read-performance`, based on published mainline dbdc05330668.
- Implementation: Created and selected the branch; preserved existing profiling artifacts and working-tree changes byte for byte. No runtime implementation change yet.
- Open: Compare a focused, permission-preserving dating read with the current summary path; require equivalent structured results before adoption.
- Risks/Assumptions: Keep ontology storage, public signatures and production unchanged. No branch push or deployment in this step.

### Update 2026-11-09 20:53
- Decisions: Diagnose current archive latency locally with exact production search payloads; production remains read-only and unchanged.
- Implementation: Owned native Jena/Flask timing and separate CPU profiles; 3-sample local/production browser waterfalls with DOM readiness, 27 loopback production search reads and 8-request local dating control. Local/production medians 1.004/4.074 s; serial local search work 68% Jena, 25% Python. Added reusable API probe and linked findings.
- Open: Class/ACL SELECT-plan comparisons, less repetitive date hydration, then fan-out/paging assessment; no runtime optimization yet.
- Risks/Assumptions: Older near-matching fixture, warm backends and different host/server topology; local shares do not establish production percentages. Observer removes polling inflation; private raw queries/profiles retained.

### Update 2026-11-09 18:17
- Decisions: Complete the approved final release; preserve existing tags and database namespace.
- Implementation: Published exact core 1.0.0 wheels/images and app 0.2.8, mainline commits/tags; scoped production activation changes only API, identity and app. Evidence in oldap-setup/docs/oldap-1.0.0-release-results.json.
- Open: Observe routine operations; retain accepted Zod 3 finding and intermittent browser timeout observation. Home unchanged.
- Risks/Assumptions: Real service and both-architecture integration checks pass; public desktop/mobile repeat passes. Read-only production smoke does not cover authenticated writes/uploads; old Compose/images retained for rollback.

### Update 2026-11-09 18:00
- Decisions: Prepare the owner-approved final 1.0.0 release; preserve independent component version lines and exact accepted runtime behavior.
- Implementation: Updated package/runtime/bump metadata where applicable; core API/Tools require final library >=1.0.0,<2.0.0 and locks retain its exact wheel hash. App includes the previously tested dependency patches; Zod 3 remains the owner's accepted temporary risk. Native service 1.0.0 compiles byte-identically to the deployed RC JAR.
- Open: Final clean-source artifacts, installed-image acceptance, immutable publication and coordinated production rollout; record exact results in oldap-setup.
- Risks/Assumptions: No deployment from this commit. Existing production images/data retained; final version labels require genuinely final package metadata.

### Update 2026-11-09 17:33
- Decisions: Preserve complete migration history in main via a non-squashed merge; keep pre-jena-merge-20261109 at the previous remote primary tip. No final release/version change or deployment.
- Implementation: Refreshed origin; primary has no unique commits and merge-tree exactly matches reviewed migration 776e70a1f706. Added current integration context only; runtime sources remain unchanged.
- Open: Verify coordinated remote refs and record final merge IDs in setup/docs/jena-mainline-merge-20261109.md. Final 1.0.0 artifact publication and old checkout cleanup remain separate.
- Risks/Assumptions: Existing deployed/candidate acceptance covers identical runtime trees; this is not a fresh full-system test. All nine checkouts were clean. Existing GraphDB checkouts and migration branches are retained.

### Update 2026-11-07 00:59
- Decisions: Avoid empty write transactions without weakening concurrent claims or replay protection.
- Implementation: Added read-only prechecks for import/export claims, export expiry/audit purge and mobile lifecycle claims; documented internal query protocol and race behavior. 271 import/export/mobile/idle tests pass.
- Open: Build/publish a new immutable API image and verify idle growth plus real jobs on home.
- Risks/Assumptions: Positive prechecks repeat transactionally; work arriving after an empty read waits for the next poll. No deployment or public signature change.

### Update 2026-11-03 23:54
- Decisions: Prepare 1.0.0rc1 for library/API/tools and the OLDAP Jena wrapper; final 1.0.0 waits for acceptance. Keep independent media/harvester versions and running environments unchanged.
- Implementation: Checkpointed HTTP pooling (e62651a) and API evidence (44cecf7). Aligned runtime/package/bump/OpenAPI/wrapper metadata; API/tools use portable 1.x requirements. Poetry solver regenerated locks offline from existing packages plus the exact new library wheel, with no path/source entry; library lock now tracked. Setup pins candidate wrapper and supports existing isolated image tags with prerelease metadata. Fixed tools bump command typo; documented local wheel/editable workflows and artifact hashes.
- Open: Final clean candidate images/home acceptance, media/harvester 1.x compatibility, production recovery/update gates and explicit package/image publication. Index installation cannot fetch the unpublished library RC; use local wheels/editables as documented.
- Risks/Assumptions: 297 installed offline tests + 26 subtests, 3 installed HTTP tests, 22 rebuilt-service checks including 300 commits, pip check, OpenAPI and three rc-to-final dry runs pass. Offline lock tests: 2 + 2 subtests; image candidate tests: 7. API/tools locks retain third-party versions; fresh pip wheel test uses declared constraints, not exact lock versions. No push, tag, merge, published image or deployment. Existing Poetry/Typer/RDFLib deprecations remain.

### Update 2026-11-03 23:25
- Decisions: Fix proven TCP port exhaustion with a per-JenaConnection HTTP pool; preserve API signatures, explicit conflict retry and uncertain-write semantics. No deployment, push or merge.
- Implementation: Library replaces per-call requests.post with an owned Session, closed on initialization failure or collection. Added real HTTP reuse/actor-isolation/no-write-retry and lifecycle regressions; adjusted transport test mocks. Recorded errno 49 diagnosis, source hashes and full acceptance in API readiness evidence.
- Open: Coordinated 1.0 dependencies/packages and final home/consumer acceptance; installed services still use previous code.
- Risks/Assumptions: 162 complete untraced integration checks pass, including unchanged stale-adoption 409. Library: 65 offline tests + 6 subtests and 3 owned HTTP/lifecycle tests; API: 61 offline + 13 subtests. Baseline used 20 TCP connections for 20 calls; fixed uses one. No shared DB/Redis; Java diagnostics were temporary and removed. Historical callback failure's own socket cause remains unproven.

### Update 2026-11-03 23:13
- Decisions: Checkpoint API migration locally, but keep merge/release blocked by reproducible full-probe 503 on stale archive adoption. Preserve public arguments, version 0.2.37 and remote/main state.
- Implementation: Reviewed backend/identity/worker-token boundaries, existing route declarations and candidate files; documented inversePath in OpenAPI and selected-backend startup. Fixed non-ASCII private identity credentials raising TypeError (now 401, three regressions). Added independent owned identity process to the synthetic probe with bounded startup/cleanup, matching deployment isolation. Retained implementation, probes, historical evidence and a candid readiness report.
- Open: Diagnose normal-speed full acceptance failure: expected stale-plan 409 becomes COORDINATION_UNAVAILABLE 503. Lightweight diagnostics identify backend Identity verification unavailable during model READ; separate verifier alone also fails. Tracing and shorter archive-only sequence mask it. Do not relax the conflict assertion or retry uncertain writes. Then complete 1.x package dependencies and final home acceptance.
- Risks/Assumptions: 61 network-blocked tests + 13 subtests pass; regression reproduced before identity fix. OpenAPI, Poetry, focused Black, syntax/JSON scans, wheel build/extracted imports and diff checks pass. Traced synthetic run passes 162 checks but ordinary complete runs fail, so no full acceptance claim. Private logs/config/data remain under /tmp; no shared DB/Redis or production deployment. Wheel still embeds sibling file dependency; existing deprecation warnings remain. Library 827bc56 unchanged.

### Update 2026-11-03 19:33
- Decisions: Accept and deploy RC4 bounded BEGIN-only retry on home. No public signature, GraphDB, worker event, lease or uncertain-write semantics change.
- Implementation: Library retries explicit BEGIN 409 with fresh journaled IDs, at most five attempts and 50/100/200/400 ms backoff. Published isolated API/tools RC4 fingerprint e3903e70a220, stable/latest unchanged; bounded client playbook updated API/identity, retained Jena/Redis/data/policy and timestamped environment backup. Real contender test passes on both local architectures and isolated native home before/after replacement, with exactly one UPDATE and COMMIT. Public home checks pass; 30-story response equals RC3, fulltext/media unchanged, 3 IMPORTED/1 INVALID and no active claims, normal worker polling.
- Open: User may run a ZIP practice test. Persistent contention and other failures still surface normally; worker lease recovery remains a separate policy. The original unlogged validation callback cause cannot be proven retroactively.
- Risks/Assumptions: Explicit BEGIN 409 proves no admission; every other admission failure retains uncertain ownership and is not retried. No UPDATE/COMMIT replay. Tests: 61 library + 3 subtests, 54 API, 29 packaged transport; native acceptance used temporary separate data and cleaned its containers/storage. Two stale resource test doubles gained the existing resolved_properties method; no resource runtime change. Evidence: sibling setup docs/jena-begin-retry-rc4-home-results.json. Production and media image unchanged.

### Update 2026-11-03 19:01
- Decisions: Package bounded Jena BEGIN-only retries in RC4; preserve public APIs, worker leases and uncertain-write recovery.
- Implementation: Sibling library uses at most five fresh-ID admissions after explicit 409 only (750 ms total backoff). Added synchronized real-service contender acceptance to setup peer; no test data on home. Sixty-one library tests plus three subtests and 54 API import tests pass. Two stale SimpleNamespace resource test doubles now provide the existing resolved_properties method; runtime resource code unchanged.
- Open: Build/accept/publish RC4 fingerprint e3903e70a220, then bounded home update and native acceptance.
- Risks/Assumptions: Persistent writer contention can still surface normally; no retry of UPDATE/COMMIT, lost replies or HTTP errors other than BEGIN 409. No production or media image update.

### Update 2026-11-03 18:35
- Decisions: Deploy private-safe import 503 diagnostics; retain public contracts, validation rules and transaction/lease behavior. Distinguish proven current BEGIN contention from the unlogged historical validation callback failure.
- Implementation: Released/deployed RC3 fingerprint 55372bad3896 on home. Native diagnostic self-test and public auth/search/media checks pass; import states remain 3 IMPORTED / 1 INVALID. Actual post-update import claims logged OldapErrorAlreadyExists in transaction_start/_send (HTTP 409), later normal 204; export polling recovered to 200. Nine setup tests, 54 local import tests, 10 packaged audit/view tests and both-architecture transport/replacement/BEGIN-contention checks pass. Client update now retains a timestamped environment backup per run. Evidence: setup docs/jena-diagnostics-rc3-home-results.json.
- Open: Original 16:39 validation callback exception cannot be reconstructed from old logs. Next improvement should address explicitly refused BEGIN admission and/or exact-event result-publication retry while retaining heartbeat; uncertain UPDATE/COMMIT must never be blindly replayed. No retry behavior was changed in this diagnostic task.
- Risks/Assumptions: Five-minute stall is the persisted worker lease after failed publication. Current contention was observed immediately after client replacement and recovered without intervention. Publishing resumed after network interruption only after exact accepted OCI digest checks; existing tags were not overwritten, stable/latest before/after unchanged. A broader network-disabled packaged test needed Redis and failed only at its staging lock; its local Redis-backed test passed, and packaged diagnostics-only tests passed. No production or media image change.

### Update 2026-11-03 17:58
- Decisions: Preserve the import HTTP contract and transaction/lease behavior while diagnosing transient validation callback 503. Do not infer the historical exception from timing alone.
- Implementation: Added bounded private-safe failure diagnostics for every mapped import 503: endpoint, correlated request ID, exception/cause types and code locations only. Excludes exception messages, source text, locals, payloads, headers and suppressed context. Twenty-one audit/view/internal tests pass, including privacy, cause cycles and unchanged public response.
- Open: Build/publish/deploy a separate home RC, then inspect observed failures. Five-minute delay is confirmed lease expiry after worker exits failed publication; overlapping Jena BEGIN admission is a candidate cause, not historical proof.
- Risks/Assumptions: No automatic transaction replay, lease shortening, validation-policy or public signature changes. Existing successful user import and earlier INVALID report retained.

### Update 2026-11-03 17:44
- Decisions: Diagnose the stalled 18.6 MB home ZIP import without resubmitting, cancelling, changing validation policy or altering job state.
- Implementation: Read-only investigation confirmed upload HTTP 201 at 16:38:51 UTC; validation report completed at 16:39:02; first validation-result callback returned 503 at 16:39:04. Worker automatically reclaimed after its five-minute lease and published INVALID at 16:44:04. Verified retained report through the API record client including checksum: three PDF_NOT_PDFA_1_OR_2 and one TEXT_INVALID_UTF8; 15 packaging artifacts ignored. No application code or deployment changed. User confirmed earlier ZIP export browser download works.
- Open: First callback's transient 503 cause is unknown: the existing handler suppresses OldapError/RuntimeError detail. Investigate diagnostic logging and retry behavior before claiming this delay is fixed. The user can inspect the now-available report and correct files. Separate observed mobile lifecycle 503 reports missing/short service JWT configuration; not changed in this investigation.
- Risks/Assumptions: The long wait was not transfer or validation throughput. Automatic recovery completed during diagnosis. No records were imported; INVALID policy already removed temporary ZIP/extraction, retaining the report. No diagnostic write/transaction was executed; a proposed abort-only probe stopped before transaction start because recovery had already cleared the claim.

### Update 2026-11-03 14:54
- Decisions: Complete the existing stalled home export, without cancellation/recreation; keep worker JWTs and public/library signatures unchanged. Production and stable/latest image tags untouched.
- Implementation: Deployed narrow Caddy Jena-only matcher and API RC2 service-account access tokens. Separate API/tools AMD64/ARM64 images use fingerprint 95c8b339149f; bounded playbook updated identity/API only, preserving Jena storage/Redis/policy. Fixed network acceptance to use the independent identity sidecar and remove both consumers before namespace replacement. Existing worker claimed the original job and reached READY: 13 files, 12,724,905 ZIP bytes, CRC/integrity and SHA256 match; build ~0.37 s, claim-to-worker completion ~1.84 s. Evidence: sibling setup docs/jena-service-rc2-home-results.json.
- Open: User downloads the ready artifact in the browser; delivery itself has not been exercised as the owner. Full import/mobile workflows remain separate acceptance work. Frozen story hash differs; RC1 and RC2 read-only requests against current data return identical 30-story responses, so no exact frozen-source parity is claimed.
- Risks/Assumptions: Original delay was queue blockage, not ZIP compression throughput. Public login/upload-auth/fulltext/media/frontend checks pass; 43 focused API tests and both-architecture packaged transport acceptance pass. New access tokens stay inside API. Caddy recreation is required after atomic bind-file replacement; reload alone sees the old inode.

### Update 2026-11-03 14:42
- Decisions: Repair stalled home ZIP export without replacing/cancelling the user's queued job. Narrow proxy isolation to the Jena namespace; service-authenticated import/export/mobile routes must remain reachable. Keep GraphDB non-token service behavior; API-owned Jena service connections issue an internal transport token using existing API signing access.
- Implementation: Corrected Caddy matcher/template and added home proxy repair playbook; atomically replaced bind-mounted configuration requires Caddy recreation, not in-container reload of its old inode. Live unauthenticated export claims now return 401 instead of proxy 404; Jena callback remains blocked. Corrected four API service-connection constructors and added both-backend regression coverage (43 focused tests pass). Preparing new isolated RC2 API/tools images and a bounded home client-update playbook; no library API/signature or worker credentials changed.
- Open: RC2 build/accept/publication/deployment running; verify existing job reaches READY and ZIP integrity/download afterwards. Extend acceptance to worker-authenticated paths, not only public read/upload probes.
- Risks/Assumptions: Original job remained QUEUED, 13 files / 12,721,419 bytes, no attempt progress. Two independent blockers: broad /internal/* proxy rule and explicit issue_access_token=False incompatible with Jena. Production and normal image tags remain untouched; internal API tokens are never returned to media workers.

### Update 2026-11-02 23:25
- Decisions: Migration Docker images use separate content-qualified Jena RC tags; keep normal versions/latest unchanged.
- Implementation: Disabled legacy Makefile docker-build/docker-push publication targets and linked the sibling setup release workflow. Published API jena-0.2.37-rc1-c1cb0919375a for AMD64/ARM64 with exact bundled migration oldaplib. Original package/version files unchanged; staged wheel version includes +jena.rc1 fingerprint. API UID/GID 100/101 retained.
- Open: Full API startup with real accounts/data, migration and coordinated activation/update; harvester release remains separate. Preserve source snapshots because these checkouts contain uncommitted work.
- Risks/Assumptions: Ten publication/deployment tests, wheel inspection, both-architecture imports/dependency/CLI/UID checks and packaged real-Jena transport acceptance pass. Published API digest also passes on native x86_64 api.home.org. Registry multiarch indexes verified; current normal version/latest digests unchanged. Initial candidates superseded to preserve runtime UID contracts; only final c1cb0919375a candidates published. Existing GraphDB/API unchanged; owned test resources removed. No Git/PyPI publication. Evidence: oldap-setup/docs/jena-images-results.json.

### Update 2026-11-02 22:58
- Decisions: Retain production migration/deployment knowledge in sibling oldap-setup migration/jena and the central cutover guide.
- Implementation: Linked the tested shared container namespace, candidate preparation and explicit migration/activation lifecycle. Updated central cutover status in oldaplib; no API/library runtime code changes.
- Open: Matched application/writer releases, full API and source/account migration, coordination recovery and automated activation/update acceptance.
- Risks/Assumptions: Bounded real identity/transaction/isolation/recreation tests pass on local ARM and remote x86_64 with synthetic data; not full application certification. Remote GraphDB stack unchanged; owned test resources cleaned up. Evidence: ../oldap-setup/docs/jena-network-results.json.

### Update 2026-11-02 12:18
- Decisions: First remote test target is home.org; no remote access in this step. Use an explicitly quiesced offline bundle, preserving admin RDF and private receipts while rebuilding derived text indexes. Restore remains isolated until operator reconciliation.
- Implementation: Added packaged backup.py with five required component directories, native TDB lock exclusion, private copy/hash/fsync/manifest verification, new-target restore and generation handoff. Extended owned service fixture for backup checks; recorded instructions and sanitized evidence in oldaplib/docs/migration/jena-backup-results.json.
- Open: Actual source/media/config inventory, home.org topology and restore acceptance, real worker fencing/coordinator reconciliation, cache isolation, matching API/tools/media releases and production cutover. Handoff metadata alone is not runtime enforcement.
- Risks/Assumptions: 40 owned service/recovery checks and seven offline tests pass. Real bcrypt user/admin-role grants, complete application/admin RDF, receipts/reservations, folded text, media/config hashes and Redis AOF recovered; post-backup commit intentionally absent. Redis pending record is a synthetic marker, not an executable production command. First harness run corrected userdata accessor; successful reruns retained. No production data/service change; owned processes stopped. Existing source generation must never be reused blindly after restore.

### Update 2026-11-02 12:01
- Decisions: Retain the private /tx protocol and single owner-thread writer; reserve each transaction UUID durably before application BEGIN. Only the separate atomic commit receipt proves success; no automatic replay or receipt expiry.
- Implementation: Shared servlet separates production from probe fault/timing hooks; built JenaService adds private strict config, fixed loopback endpoint, explicit initialization/reopen, health and signal shutdown. Pinned offline JDK25/Fuseki6.2.0 build, manifest/hashes, launcher and uninstalled systemd/launchd templates. Query execution bounded to 60 s; fulltext unavailability is visible across threads. Context/operator docs updated.
- Open: Full backup/restore including reservations/receipts, actual account/data migration, supervisor/worker deployment acceptance and sustained mixed-write load. Receipts/admissions grow on disk; no pruning policy. Service initialization is empty and is not a production switch.
- Risks/Assumptions: 22 packaged checks incl. 300 commits and fulltext/crash restart; 20 identity, 20 session, 11 callback, 50 managed-text checks and 18 offline tests pass. Two identical builds verified. Initial reservation-conflict cleanup corrected and suites rerun; library-only environment lacked pytest/API fixture dependencies, so tests used sibling API environment. Evidence: oldaplib/docs/migration/jena-service-results.json. Existing GraphDB/API/Redis untouched; owned processes stopped. No public signatures changed.

### Update 2026-11-02 11:46
- Decisions: Measure the current public story-overview API dependency chain before any further optimization; preserve parallel keyword/search reads and subsequent 100-IRI summary batches.
- Implementation: Added documented probe_story_overview.py using the existing owned preview harness; retained sanitized timings/fingerprints and method in doc/graphdb-jena-python-comparison.md. No application/runtime changes.
- Open: Browser render/image/capability/login timing, cold starts and production-capacity acceptance are outside this measurement; continue the persistent-service readiness work.
- Risks/Assumptions: 28 stories/28 lead images; 20 warmed workflows/backend, 120 timed HTTP requests pass. Full story/summary parity, rubric parity excluding recreated provenance, complete per-backend stability and source checksum preservation. GraphDB/Jena all-metadata medians 134/158 ms (~17%); text-ready 57/86 ms. Preliminary runs stopped on provenance mismatch before timing. Unequal local deployments; owned services stopped. Python compilation and diff checks pass.

### Update 2026-11-02 11:38
- Decisions: Jena/Fuseki is the production target; prioritize deployment and recovery readiness over marginal benchmark gains.
- Implementation: Reviewed migration/service/deployment sources and retained acceptance evidence; added ordered launch gates, acceptance criteria and next service slice to the shared cutover index; linked stable context in all three migration repositories.
- Open: Persistent service/identifier lifecycle, full restore rehearsal, actual accounts and source migration, versioned artifacts including mediahelper, production worker/write/soak acceptance and controlled cutover.
- Risks/Assumptions: Documentation/source review only; no tests rerun, services changed or production migration performed. Java probe stops admitting new transactions after 256 identifiers, uses stdin lifecycle and retains test hooks. Historical evidence is not current release acceptance; initial project scope remains to be confirmed.

### Update 2026-11-02 01:34
- Decisions: Repeat the unchanged six-case read-only GraphDB/Jena workload after Python/model/payload optimizations, with 8 GiB Jena and 1/4/8 reader waves. Repeat once more because GraphDB run 1 had slow tails; retain both runs.
- Implementation: Measurement/documentation only, existing harness unchanged. 624 timed requests pass; all six cross-backend cases agree and complete per-backend responses stay stable. Evidence: doc/graphdb-jena-python-comparison.md.
- Open: Counts and dated searches still favor GraphDB; larger paired data, authenticated roles, equal-deployment and write/soak studies. No engine-only or production-capacity conclusion.
- Risks/Assumptions: Confirming GraphDB/Jena medians 57/73, 117/139, 203/250 ms at 1/4/8 readers; Jena ~19–28% slower versus prior ~2–2.5×. Jena repeats stable; GraphDB run-1 p95 outliers did not recur. Source unchanged; owned services stopped, original GraphDB/deployment untouched. No runtime changes; diff checks pass.

### Update 2026-11-02 01:27
- Decisions: Keep JSON-LD/decoder: exploratory format switching was not faster. Reduce redundant graph data instead; materialize Jena summary role/permission nodes in a bounded independent subquery before property/type joins. Preserve GraphDB expression and all outer authorization checks.
- Implementation: Commented summary builder change; native regression checks four independent grant nodes for two multi-role resources. Evidence: doc/jena-summary-payload.md; no public signatures, stored RDF or transport changes.
- Open: Concurrent performance, optional single-resource payload optimization and deferred GraphDB countercheck. The former date UNION rewrite remains rejected; no general decoder/format machinery introduced.
- Risks/Assumptions: Two ABBA runs preserve 120 complete API responses; dated pages 306→231 / 320→241 ms (~24–25%). Graph 4799→1799 triples; response 575509→195509 bytes. Larger copied 12000-extra-record fixture remains faster (~48→39 ms bounded native summary). 209 native and 29 focused checks pass; missing test import corrected and native suite rerun. Source unchanged; owned services stopped; original GraphDB/deployment untouched. Compilation/diff checks pass.

### Update 2026-11-02 01:18
- Decisions: Fresh post-validation profile identifies repeated superclass/model reconstruction; per-result class/property resolution is too small to optimize. Reuse independent copies of Redis-loaded ResourceClass snapshots only during synchronous factory/model construction, following the existing project-read scope.
- Implementation: Context-local connection/project/class scope, copy isolation/current connection, exception cleanup and forced-reload/transaction bypass; three behavioral tests. Test-only previous-reader ABBA control and sanitized evidence: doc/jena-model-read-reuse.md.
- Open: JSON-LD transport/decoding and native dispatch remain larger costs; concurrent performance and later GraphDB countercheck. No public signatures, SPARQL or API runtime changes; original GraphDB/deployments untouched.
- Risks/Assumptions: Two ABBA runs preserve 120 full responses; dated page medians 322→281 and 300→271 ms (~10–13%), other cases broadly unchanged. 42 profiling requests, 208 native checks, 32 library tests and six API tests pass. Scope copies mutable models, never authorization/resource results; only successful Redis hits retained. Source unchanged; owned services stopped. No production-capacity claim.

### Update 2026-11-02 01:08
- Decisions: Trust database RDF after write-time validation; use existing validate=False/fromRdf on reads, preserving new-input/token validation and authorization. Retain bounded compiled datatype schemas, never values or access results. Reject both count EXISTS and date UNION query experiments; original objectfactory fully restored.
- Implementation: Explicit trusted CONSTRUCT decoding, gMonthDay honors validate, date expansion preserves typed RDF class names; finite XMLSchema reuse and focused tests. Same-target profiler controls and sanitized evidence: doc/jena-validation-performance.md.
- Open: Concurrent/load measurement of retained changes and later GraphDB countercheck; comprehensive repository-wide validation-boundary audit. Legacy datatype integration requires missing GraphDB oldap-test fixture (44 setup errors).
- Risks/Assumptions: 208 native PASS checks (including growth/revocation), 41 library tests, six API tests and 60 equal HTTP responses pass. Serial count 82→60 ms; date page 367→278 ms; timings isolate schema reuse, not read-path changes. EXISTS regresses at 12000 records; UNION regresses date HTTP. Source unchanged; no public signature, original GraphDB or deployment change.

### Update 2026-11-02 00:43
- Decisions: Repeat the unchanged six-case GraphDB/Jena comparison after dating precheck, using 8 GiB Jena and fresh measurements of both backends. No runtime changes in this step.
- Implementation: Retained 312 successful measured requests with six-case equivalence and exact per-backend stability. GraphDB/Jena medians at 1/4/8 readers: 57/118, 132/270, 199/488 ms. See doc/graphdb-jena-precheck-comparison.md.
- Open: Actual dated hydration/count-query costs; larger/role/write/soak and equal-deployment studies. Jena medians are 14–22% below the previous 8 GiB run, but GraphDB also varied; backend ratio does not improve uniformly.
- Risks/Assumptions: Same small real-data source; two serial samples/case, empirical p95. Unequal deployments, no production-capacity claim. Source hash unchanged; owned services stopped; no deployed changes. Diff checks pass.

### Update 2026-11-02 00:39
- Decisions: Use a conservative live SHACL eligibility ASK before constructing the dating factory. Match requested direct/inverse fields across project/shared/base shapes regardless of owning class; preserve all positive-case hydration and permission checks.
- Implementation: API helper/early return, focused model/batch/permission tests, same-target ABBA profiler mode and retained evidence: doc/jena-dating-precheck.md. Library runtime unchanged; migration index updated.
- Open: Actual date model reconstruction/hydration and dated queries remain. Serial metadata median 157→119 ms (~24%), text 162→118 ms (~27%); dates ~361→357 ms, not an established improvement and now one extra ASK. No concurrent capacity claim.
- Risks/Assumptions: 60 full-response-equal API requests, 23 native fixture checks, ten focused tests and two read-only GraphDB ASK compatibility checks pass. Future/removed/inverse declarations verified on live owned model. Source unchanged; owned services stopped; no public signature or deployment change. Compilation/diff checks pass.

### Update 2026-11-02 00:33
- Decisions: Decompose the same six searches without changing application behavior. Measure private Java token verification/dispatch, backend HTTP, API processing and nested hydration separately; cProfile runs are excluded from timing medians.
- Implementation: Shared benchmark case definitions, owned sequential profiler and opt-in timing headers on all successful private probe routes. 42 full-response-stable requests, 23 fixture checks; source hash unchanged, owned services stopped. Evidence: doc/jena-backend-profile.md.
- Open: First remove model/factory/list preparation for searches without Dating-valued requested fields (~54–56 ms inclusive). Preserve inherited/future field support. Then model hydration and dated SELECT/CONSTRUCT profiling; no optimization applied yet.
- Risks/Assumptions: Five timing samples/case, 8 GiB local fixture. API-other includes Redis/instrumentation; dispatch includes parsing/serialization; nested spans cannot be added. Token verification ~6 ms/call, transport residual ~2–8 ms/request. GraphDB internals not profiled. Compilation/native fixture/diff checks pass; no public signature/security behavior change.

### Update 2026-11-02 00:27
- Decisions: Test a generous 8 GiB owned Java heap, then a fresh 512 MiB control on the identical read workload. Preserve the 512 MiB default and set only Xmx.
- Implementation: Added --java-heap-mb to the owned API runner, positive-limit validation, private PID/heap metadata and sanitized benchmark heap reporting. Retained both reports in doc/jena-heap-comparison.md; jcmd verified both heap ceilings before timing.
- Open: Profile API/transport/query costs; larger datasets, peak/GC measurements and repeated capacity trials remain separate. Jena medians 512 MiB→8 GiB: 156→152, 341→331, 591→570 ms (1/4/8 readers), only ~3–4% and not statistically established.
- Risks/Assumptions: 624 timed requests pass across two runs; all six cases agree, source hashes unchanged, owned services stopped. JVM ergonomics and host variation limit causal interpretation. CLI help, compilation, invalid-limit/no-side-effect and diff checks pass. No shared-service or public API changes.

### Update 2026-11-02 00:12
- Decisions: Establish a bounded read-only GraphDB/current-Jena real-data baseline before further optimization. Compare all projected values and page order; exclude engine-specific relevance scores only across title-sorted backends, never within backend stability checks.
- Implementation: New owned comparison runner, six public ArchiveObject cases, warm alternating 1/4/8-reader waves, source export fingerprints and sanitized results. 312 timed HTTP requests pass; all six cases agree. See doc/graphdb-jena-performance.md (API repository).
- Open: Equal deployment/heap comparison, authenticated roles, media/linked text, larger paired datasets, soak/writes; profile measured API/transport/query costs next. GraphDB/Jena mixed medians: 61/164, 128/315, 205/579 ms.
- Risks/Assumptions: Existing GraphDB/API versus disposable 512 MiB Jena/threaded API; only two serial samples/case, empirical p95, no engine-only or production-capacity claim. Source byte-stable; owned services stopped. No application runtime/signature/deployment change.

### Update 2026-11-02 00:03
- Decisions: Rehearse optimized queries at 1/4/8 simultaneous requests with 100-row pages, readable dates and complete fulltext candidates. Preserve the old load report as historical evidence, not a controlled A/B comparison.
- Implementation: Test-only harness updates: explicit date grants/independent serialized-year validation, 100-row workload, fulltext total/tail assertions and help handling. Retained aggregate evidence in doc/jena-search-load-optimized.md; no application runtime changes.
- Open: Production CPU/memory/multi-process load, soak/concurrent writers, frontend grouped paging and GraphDB comparison. Medians 1.25/1.88/2.99 s; eight-request maximum 5.33 s. No production-capacity claim.
- Risks/Assumptions: 211 checks/209 measured HTTP requests pass, including all 130 reader-wave responses and post-wave revocation; 30 fulltext/23 API fixture checks pass. Local 512 MiB Java, two identities, unchanged timeouts. Source hash unchanged; owned services stopped. No public signature, shared-service or deployment change.

### Update 2026-11-01 01:31
- Decisions: Resolve schema relationships before instance joins uniformly; preserve every inverse/subproperty rule, scope and permission check. No schema cache or field-specific query branches.
- Implementation: Reordered modeled-inverse definitions, legacy inverse joins and subproperty branches in the shared Jena property pattern. Extended owned paging probe with trusted pre-edit helper comparison, ABBA order, full-response equality and private query plans. See doc/jena-search-candidates.md.
- Open: Production memory/concurrency, frontend grouped pagination and deferred GraphDB comparison. Local public metadata/date/text HTTP medians improve 3.31→0.53 / 5.59→1.27 / 3.34→0.77 s at the same 100 rows; production capacity is not established.
- Risks/Assumptions: 198 assertions/64 HTTP requests, 30 fulltext/23 API fixture checks, 208 native/growth and 24 focused offline tests pass. Two samples per plan/shape on owned 512 MiB Java. Shared helper also serves reads/summaries; no public signature or GraphDB query change. Source unchanged; owned services stopped.

### Update 2026-11-01 01:20
- Decisions: Keep this step in API/oldaplib; retain 100 as the existing default, with larger explicit limits supported. Fix correctness before tuning broad queries further.
- Implementation: Counts omit sort-value joins. Jena text requests explicitly cover the Lucene document domain: omitted/nonpositive limits silently capped candidates at 10000 before ACL checks. Added 12000-resource page-size/deep-page/count/revocation rehearsal; shared fixture seeding. See doc/jena-search-pagination.md.
- Open: Candidate/property/date joins before LIMIT dominate; frontend grouping/pagination, production memory/concurrency and GraphDB countertest remain separate. 214 checks/76 HTTP requests, 30 fulltext/23 API fixture checks, 189 native and 83 offline checks pass. Date pages public 8.83→5.25 s, audit 14.29→7.20 s at LIMIT 100 versus 5000; ordinary metadata/text latency changes little.
- Risks/Assumptions: Legacy control counts only 5000/7500 versus corrected 6000/9000. Full-index text candidates/collector remain memory-sensitive; no streaming claim. Two sequential timing samples per shape on local 512 MiB Java. No signature, ontology, index rebuild or frontend change. Source unchanged; owned services stopped.

### Update 2026-11-01 01:00
- Decisions: Test bounded growth and concurrent readers before further optimization; retain functional success and latency limits separately. Do not raise test-server limits or introduce a cache.
- Implementation: Owned API load harness with 1000/4000/12000 synthetic records, independent expected visibility/order, complete traversal, 5000 window and 1/4/8 concurrent requests. Evidence: doc/jena-search-load.md. Pilot setup exhausted the 256 completed-transaction budget; fixed fixture insertion to one transaction per stage.
- Open: All 207 load checks and 130 concurrent requests pass; 6000 public/9000 audit IDs traverse completely and revocation is immediate. Median broad-query latency 4.32/9.01/18.03 s at 1/4/8 requests. Frontend paging/completeness and broad date/property query profiling are next; production/soak/writes/GraphDB remain open.
- Risks/Assumptions: Local 512 MiB Java fixture and development API, two authorization profiles, broad synthetic matches. Pre-growth 30 fulltext/23 API checks pass. No runtime/public contract changes. Source hash unchanged; owned services stopped.

### Update 2026-11-01 00:33
- Decisions: Reduce repeated namespace resolution inside one CONSTRUCT graph, without changing queries, permissions or batch limits. Keep fresh QName instances and discard the lookup after each graph.
- Implementation: Local known/unknown URI memoization plus processor documentation; new context/mutability regressions. Extended metadata profiler with a trusted pre-edit processor comparison and separate decoding timings. Evidence: doc/jena-dating-hydration.md.
- Open: Remaining transport/JSON-LD and model/date conversion costs; production/browser load and deferred GraphDB comparison. 188 native, 30 fulltext API, 23 export and 49 offline checks pass; all 24 comparative responses equal.
- Risks/Assumptions: Two local samples per shape; hydration ~1.00→0.76 s, whole object request ~1.60→1.36 s. Common processor affects both backends; no public contract change. Source hash unchanged; owned services stopped.

### Update 2026-11-01 00:27
- Decisions: Use whole-triple grant extraction for broad Jena searches; retain direct lookup for text/relationship candidates. Reject grouping-only plan and the growth regression from applying extraction to relationship searches.
- Implementation: Local ACL branch with shared relationship-candidate selection; six date boundary/operator checks and adversarial grant validation. Added owned six-case profiler, response equality and retained evidence in doc/jena-metadata-performance.md.
- Open: Broad object-list date hydration remains ~1 s; production load, browser timing and deferred GraphDB comparison remain open. 207 native/growth, 30 fulltext API, 23 export and 40 offline checks pass; 24 comparative responses agree.
- Risks/Assumptions: Local two-sample timing, uncontrolled host load; no production capacity claim. Public signatures, GraphDB path and source export unchanged. Owned services stopped; no deployment.

### Update 2026-10-31 23:55
- Decisions: Validate approved accent/umlaut/ß folding through the normal API and YAML activation, without stemming or source-text rewriting.
- Implementation: Extended owned fulltext acceptance with pre-existing decomposed Unicode text in a new field; checks exact/folded/prefix queries, distinct singular/plural and unchanged API read values.
- Open: 30 fulltext API and 23 real-export checks pass; 26 timed queries have median 87.5 ms, maximum 581 ms. Production load and deferred GraphDB comparison remain open.
- Risks/Assumptions: Disposable fixture only; analyzer implementation and rebuild guidance live in oldaplib. No API signature change or live service deployment. Source SHA-256 unchanged; owned services stopped. Stored decomposed text survives indexing and restart unchanged; no deployment or shared-service changes.

### Update 2026-10-31 23:43
- Decisions: Evaluate Jena text candidates before root ACL/property/list joins, after independent class selection. Preserve all permissions, scores, ordering and paging; use the simple reorder rather than an extra grouping layer.
- Implementation: Updated shared result/count query order with comments; added owned six-shape, three-plan HTTP profiler and retained timings. All 54 comparative responses are equal; per-shape medians improve from 1671–3303 ms to 56–143 ms. Updated native multiword expectations to the agreed AND semantics.
- Open: Production load and analyzer/language behavior; GraphDB countertest remains deferred. Browser timing also includes metadata requests/rendering.
- Risks/Assumptions: 169 native, 26 fulltext, 23 export and 27 offline checks pass. Final normal-adapter run: median 76 ms across 22 timed searches, maximum 493 ms. Browser confirms the same 20 matches. Source SHA-256 unchanged; owned services stopped. Public contracts and GraphDB query placement unchanged.

### Update 2026-10-31 23:28
- Decisions: Rehearse fulltext on the owned real Fasnacht export with isolated Redis and normal tools/API paths. GraphDB countertest remains deferred.
- Implementation: Added optional --fulltext-preview acceptance: nine YAML fields, title/PDF/phrase/prefix/count/paging, multiword and multivalue matching, future property activation, root/source permission revocation, and concurrent class search.
- Open: 26 fulltext and 23 real-export checks, 46 index lifecycle checks, and 61 offline tests pass. Browser confirms 20 matches (14 media, five objects, one event) with both word orders. Production performance/analyzer acceptance and GraphDB comparison remain open.
- Risks/Assumptions: API/lib/tools offline checks: 27/13/21 passed. Internal PDF text was absent in the export and was tested with a synthetic marker only in the disposable target. Source SHA-256 unchanged; owned API/Jena/Redis and Vite stopped. No live services or public signatures changed.

### Update 2026-10-31 22:59
- Decisions: Match existing SIPI minimum DATA_RESTRICTED=1; require valid numeric permission and asset binding. Only absent credentials may use public lookup; keep public API signatures unchanged.
- Implementation: Updated owned Caddy/mediahelper rehearsal to mount repository source read-only and assert 403 for invalid/expired/wrong-asset/zero-permission capabilities; retained tokenless public success. Full mediahelper suite: 374 passed, 20 skipped, four subtests; owned HTTP: 23 API, ten image and nine grouped asset checks pass. Black/Poetry/diff pass (existing Poetry deprecations).
- Open: Rebuild/version and explicitly deploy mediahelper to activate; no live service changed. Automatic token expiry renewal and uploads remain separate migration gates.
- Risks/Assumptions: Existing capabilities keep their bounded lifetime. Formerly tolerated malformed capabilities now return 403; callers must omit credentials for public lookup or obtain valid tokens. Source hashes unchanged; owned services stopped.

### Update 2026-10-31 22:49
- Decisions: Rehearse PDF/original delivery through unchanged installed Caddy/mediahelper using owned copies and keys; report policy differences separately from transport success.
- Implementation: Added --asset-service-root and preview_assets.py with eight grouped byte/range/authorization checks and two policy diagnostics. Frontend local non-IIIF capability omission fixed; authorized PDF page navigation verified. 23 API, ten image and two offline checks pass; source hashes unchanged; owned services stopped.
- Open: Mediahelper accepts correctly signed permval=0 and falls back to public lookup for invalid supplied tokens. Enforce agreed permission threshold and fail-closed handling before cutover; automatic expiry renewal/uploads remain untested.
- Risks/Assumptions: No API signatures or live services changed. Existing frontend Map lint error reproduced before/after; production build passes. macOS Docker Desktop and installed image tags required.

### Update 2026-10-31 22:42
- Decisions: Validate signed image delivery using one copied real derivative and an owned loopback-only SIPI container; preserve public contracts.
- Implementation: Added optional browser --media-root fixture, capability/CORS/HEAD/revocation/negative checks and reproducible evidence. 23 API, ten media and two offline checks pass; browser image/zoom/reset verified; source hash unchanged and owned services stopped.
- Open: PDF/original downloads/uploads, anonymous fallback, automatic expiry renewal, production cache/load and remaining browser workflows.
- Risks/Assumptions: Requires installed SIPI 0.1.3 and the known Fasnacht derivative; issued capabilities remain valid until expiry. Private source/output stay outside Git.

### Update 2026-10-31 00:50
- Decisions: Verify existing FasnachtsPage against an owned real-export Jena/Redis target; retain public versus audit identity separation and leave source/live systems untouched.
- Implementation: Added bounded --browser-preview acceptance support, public fixture role, source Chama namespace registration and one private synthetic child. Browser verified overview counts, 48→96 expansion, title sorting, parent/child navigation, anonymous denial, audit access and logout isolation. No frontend/application runtime change.
- Open: Media binaries/capability integration, fulltext activation, direct archive-unit assignment UI fixture, real accounts and production acceptance. Denied detail wording is raw HTTP 404.
- Risks/Assumptions: Missing source-role namespace initially caused fresh audit-token rejection; disposable admin namespace provisioning fixes it without changing token format. Source has 20 readable units but zero direct archiveUnit assignments. Screenshots/evidence retained; owned processes are stopped after testing. No commit, push or production mutation.

### Update 2026-10-31 00:36
- Decisions: Check warm-cache reads across acknowledged permission mutations with four independent HTTP clients. Allow either committed snapshot only for overlapping requests; require fresh authorization for every post-acknowledgment request.
- Implementation: Extended owned --cache-only acceptance with barrier-started search/count/detail phases, distinct per-worker sessions, object/user-role revocation and restoration, and aggregate overlap evidence. No runtime or public API changes.
- Open: Production load capacity, multi-process/browser acceptance and real-user migration parity remain open. Existing stateless access-token deactivation policy is unchanged.
- Risks/Assumptions: All 26 focused HTTP checks pass, including 168 concurrent-phase requests. Mutation windows overlap 16 object-grant and 13 role-change requests; all 48 post-revocation requests deny visibility. This proves client-request overlap, not database internal parallel execution. Owned services stopped; no shared Redis access, commit or push. Syntax and whitespace checks pass.

### Update 2026-10-31 00:33
- Decisions: Accept warm-cache relationship search/detail authorization with actual isolated Redis; preserve the documented stateless access-token policy instead of introducing immediate account revocation silently.
- Implementation: API runner adds --cache-only using existing socket-only owned Redis (cache DB 0, coordination DB 1), with no mocked cache methods. New checks cover identity isolation, values, object grants, orphan annotations, existing-token role removal/restoration, login/refresh deactivation and documented access-token lifetime. No application runtime/signature changes.
- Open: Production cache/browser/concurrency and representative-user migration acceptance remain open; immediate account-wide access-token revocation remains outside the current authentication contract.
- Risks/Assumptions: 17 focused HTTP checks and 16 offline tests pass. Warm-cache phase records 45 Redis hits, 19 final cache keys. Existing access tokens remain valid until expiry (default 15 minutes) after account deactivation; login/refresh are refused. Initial fixture restored independent owner rights and corrected token-policy expectations. All services/data were owned and stopped; no shared Redis access, commit or push.

### Update 2026-10-31 00:28
- Decisions: Validate larger relationship result sets before further optimization. Keep independent class-set selection before relationship candidates, then preserve all original ACL/filter checks; no public signature changes.
- Implementation: Corrected query order after a 1,000-child count exceeded the 10-second timeout. Added opt-in --relationship-growth fixture with chunked rollback-only updates, 120-second test transaction lease (request timeout unchanged), complete tied-name paging, subproperties, orphan/restricted grants, AND order, revocation and rollback checks. Recorded aggregate timings and documentation.
- Open: Production concurrency, real identities and cache/browser acceptance remain open.
- Risks/Assumptions: All 185 native checks, 27 offline tests and 24 real-export API checks pass. Real Fasnacht HTTP medians remain 452 ms project-wide / 946 ms class/name/sorted; all five parent comparisons match. Synthetic median count 339 ms, first page 452 ms, ten-page traversal 477 ms/page; library transport, not HTTP API. Initial fixture request-size and total transaction-lease limits were corrected without changing production limits. No live data mutation, commit or push.

### Update 2026-10-31 00:21
- Decisions: Optimize mandatory root EQ-IRI/QName searches by selecting distinct relationship candidates before class/ACL joins; retain original filters, property semantics and permission checks. Skip candidate selection for expressions containing OR. No public signature or GraphDB behavior change.
- Implementation: Added one documented local query-builder function and ten native regression checks for permissions, subproperties, duplicate paths, Boolean filters, paging/counts, graph scope, revocation and rollback. Retained diagnostic profiling helpers/native benchmark, aggregate evidence and performance guide from the analysis. Updated cutover context.
- Open: Production load, cache/browser and real-user migration acceptance remain separate.
- Risks/Assumptions: First eligible relation is used without selectivity statistics. No permission cache or stored reverse edges. 166 native checks, 27 offline tests and 24 focused API checks pass. Real-export HTTP medians: project-wide 7355→524 ms, frontend shape 3054→924 ms; all five parent comparisons pass. Measurements use isolated owned data only. No live changes, commit or push.

### Update 2026-10-30 23:58
- Decisions: Use a fresh read-only local TriG-star export after archived gzip input was correctly refused for encoded RDF4J triple IRIs. Retain any original account header privately; never silently drop or activate accounts.
- Implementation: Added read-only exporter, private preparation/header retention, native instance extraction and real-data/API comparison in the owned fresh-model runner. Retained aggregate evidence and cutover guidance. No application API/signature change.
- Validation: Real local Fasnacht TriG-star export rehearsed on a fresh owned Jena target: 38,674 instance triples, two hasPart reversals, 11 canonical pairs, all 38,663 other triples unchanged. All 23 focused checks pass, including five parent API comparisons and a single-resource read. Source export byte-stable. Native conversion preserves 35,829 ordinary source quads and converts 2,919 annotations, with zero orphaned annotations or added memberships and successful structural round-trip. One subject link preserved; no direct archive assignments existed or were manufactured. Python compilation/whitespace pass; owned processes ended. Initial Java Dataset cleanup compile issue corrected before successful run.
- Open: Production snapshot rehearsal, actual-account/role provisioning and user-specific permission parity, binary/fulltext/cache/browser acceptance; reverse-search trace takes several seconds per request and needs performance work.
- Risks/Assumptions: Current local data, not production. Owned audit actor receives nine source role identities only in disposable admin graph; instance permissions unchanged. Old source model/lists retained privately; target uses revised YAML. No live mutation, cache flush, deployment, commit or push.

### Update 2026-10-30 23:46
- Decisions: Prove complete model provisioning on a fresh owned target before in-place cleanup or real-data cutover.
- Implementation: Added focused --fasnacht-only API acceptance and complete YAML/taxonomy CLI import, no-write replay, transactional part conversion and HTTP permission-filtered reverse lookup. Retained hashes, counts, evidence and cross-repository context. No runtime application change required.
- Validation: The actual migration YAML imports through tools/HTTP with 16 classes, 88 property declarations, 10 taxonomies and 3 external registrations. 224 operations, then zero-write replay. Canonical isPartOf reverse lookup excludes an ungranted child after transactional conversion. All 13 focused checks pass. Owned processes completed; Python compilation and whitespace checked.
- Open: Actual Fasnacht export comparison, in-place shape/restriction cleanup, fulltext activation and browser/cache acceptance. Chama relations remain separate.
- Risks/Assumptions: Fresh target and synthetic instances, not production acceptance. GraphDB connectors skipped. External registration does not imply graph content loading. Object-cache I/O suppressed; no live source/data/Redis changes, deployment, commit or push.

### Update 2026-10-30 23:28
- Decisions: Verify explicit inverse metadata removal through the actual tools CLI and normal HTTP model-update endpoint, without substituting SPARQL schema cleanup.
- Implementation: Added an owned HTTP/tools migration fixture and wired it into the normal API acceptance runner. Updated context, guide and sanitized evidence; existing runtime/API code required no change for inverse removal.
- Validation: 162 integration checks pass, including eight new archive checks. Legacy false assignment reproduced; preview, backup, metadata/RDF removal, stable direct response, unchanged instance triples and zero-write replay verified. Backup retains prior metadata and RDF. Syntax/whitespace checks pass; owned processes completed.
- Open: Full Fasnacht target import/real-data comparison, cache acceptance, reverse/external axiom inventory and general modeled inverse fields.
- Risks/Assumptions: Minimal demo namespace/class fixture uses actual Fasnacht target/cardinality/null declaration. Only forward axiom owned by the edited property is covered; object-cache I/O is suppressed. No live data/service changes, public signature changes, commit or push.

### Update 2026-10-29 00:45
- Decisions: Implement a limited, explicit read-entailment contract rather than enable general OWL reasoning. Keep public API/library signatures, GraphDB behavior and asserted-only authorization/provenance. Preserve existing asserted-only search projections while filters/summaries support derived links.
- Implementation: Added shared inverse/class/schema helpers and transaction-local external vocabulary discovery; wired resource reads/summaries/search and media/archive class checks. Class search preselects instantiated types before ACL joins to avoid repeated ontology walks. Rehearsal preserves used source prefixes, compares eight additional batch/search cases, verifies adversarial/transaction scenarios and measures isolated cache/scale/control cases.
- Validation: All 112 original plus eight extra GraphDB/Jena HTTP comparisons match; all source bracketing guards pass. Seven native entailment checks, 126 model/search checks, 154 API checks and 41 offline tests pass. Added scope/cycle/type/provenance/registration tests. Real Chama plus 1,000 synthetic people measured; paired search control requires identical pages. Syntax/whitespace checks pass; owned services closed after probes.
- Open: Broader real-project/load/concurrency acceptance; durable prefix/vocabulary provisioning for deployment, fulltext inverse-path decisions, large export/account/binary migration and production recovery. General OWL restrictions/domain/range/sameAs/property chains remain unsupported.
- Risks/Assumptions: Warm single read 141→175 ms and 54-resource summaries 311→414 ms; not negligible overhead. Cold means object cache only. Broad scaled search ~1.19 s; identical-page Person control 0.90 s new vs 1.72 s previous-rules control, not a historical release benchmark. Schema discovery and data read are separate outside a transaction. Source/user Redis untouched; private exports outside Git. No deployment, commit or push.

### Update 2026-10-29 00:04
- Decisions: Rehearse a real GraphDB project with an isolated Jena API, preserving asserted source data and public contracts. Keep content mismatches visible rather than accepting inferred-data loss or enabling general OWL reasoning.
- Implementation: Added repeatable Chama export/conversion/provisioning/import/API comparator, private evidence and sanitized report. Source schemas plus three vocabulary graphs, limited two-account bootstrap, normal API and owned Redis. Replaced exponential dataset tuple comparison with graph-based quad verification; reject RDF4J encoded triple URIs and use explicit star export formats.
- Validation: Real transfer succeeds; 112 API statuses match, 77 normalized bodies match and 35 differ (27 inferredTypes, eight knowledge backlinks, one story hasPart; overlapping fields). Source project/schema/admin exports and API baselines stable on reread. 28 native converter and eight CLI checks pass; syntax/whitespace checks pass. Owned services stopped.
- Open: Scoped external vocabulary hierarchy/equivalence and inverse-property reads; rerun the same comparator before claiming parity. Fulltext/binaries, further actors, writes, large packages, snapshot/recovery and production cutover remain separate gates.
- Risks/Assumptions: Rehearsal exits nonzero deliberately for content differences. Arrays compared without order; source uses existing cache. Bracketing stability is not a coordinated snapshot. Two pre-existing admin orphan grants preserved without memberships. Private exports/hashes/responses outside Git; no source data writes, deployment, commit or push.

### Update 2026-10-28 23:44
- Decisions: Retain GraphDB-to-Jena migration knowledge explicitly for the later system transition, as requested by the user.
- Implementation: Added a central cutover knowledge index in oldaplib and prominent links in all three repository master contexts. Records proven tools/evidence, compatibility/reasoning decisions, limits, administrative and binary/index gaps, rehearsal sequence and recovery prerequisites.
- Open: Representative source project export, controlled target provisioning/import/API comparison and remaining production cutover gates.
- Risks/Assumptions: Documentation only; checklist is future work, not production acceptance or authorization to switch systems. No runtime changes, service access, commit or push.

### Update 2026-10-28 23:16
- Decisions: Add a native RDF 1.2 graph-transfer boundary for provisioned projects; retain existing public signatures/GraphDB behavior. Require current root rights and explicitly exclude administrative identity restore. Preserve cross-graph blank nodes without Python RDF reserialization.
- Implementation: Added JenaProjectTransfer native parser/serializer and three session operations, private adapter export/import methods, explicit tools project routing and versioned gzip headers. Export replaces files atomically; import validates graph scope then appends within existing transaction ownership. Cache checked before import and cleared after commit with explicit committed-state errors. Added docs, offline tests and owned CLI/Redis acceptance.
- Validation: 154 integration checks pass (145 previous plus 9); 14 library and 17 tools tests pass. Covers four-graph RDF 1.2/language/blank-node round-trip, ordinary-user/root-revocation refusal, joined rollback, malformed/foreign/default/reserved input, and fulltext commit/rollback. Corrected initial fixture short-name datatype. Owned processes closed; whitespace checks clean.
- Open: Full administrative users/roles restore, legacy GraphDB RDF-star conversion, streaming/large projects, binary/export-job acceptance, production cache/concurrency and normal-adapter crash recovery.
- Risks/Assumptions: Jena --no-admin dumps are not complete backups; target project namespace/identities/configuration must be provisioned separately. Existing 262144-byte JSON request limit remains; server export uses memory. Import appends, so repeated blank-node payloads are not idempotent. CLI migration assumes quiesced application traffic; no production services, public signature changes, deployment, commit or push.

### Update 2026-10-28 23:00
- Decisions: Preserve public media signatures, serialization and token claims; select project-scoped media ancestry and asserted RDF 1.2 grants on Jena. Refuse ambiguous visible identities instead of merging token metadata.
- Implementation: Added documented private media query helper and backend routing for ID/IRI lookup. Bind selectors/caller inside permission aggregate. Added owned modeled-media/inventory acceptance, dedicated Redis fixture naming, isolated media JWT key, offline routing/ambiguity tests and retained results/documentation.
- Validation: 145 owned integration checks pass (132 earlier plus 13 new); 18 library tests plus 6 subtests and 10 API tests pass. Real HTTP covers metadata/signed claims, restricted grants, paginated hydrated inventory, entry capabilities, catalogue references, revocation/orphans, duplicate IDs and unrelated schema isolation. All owned processes closed; diff whitespace checks pass.
- Open: Raw project transfer/export, production object cache, normal-adapter crash/uncertain-outcome recovery and binary media delivery.
- Risks/Assumptions: Shared-model fixtures and real policy/coordination; object-cache I/O suppressed. Catalogue reference edge and malformed edge cases imported directly for acceptance. Candidate discovery and metadata reads are separate outside an existing transaction; metadata queries recheck rights. Existing tokens are not revoked by lookup changes. GraphDB query path unchanged; no public signature change, deployment, commit or push.

### Update 2026-10-28 22:50
- Decisions: Exercise full adoption through real policy-file loading, durable Redis coordination and HTTP endpoints; preserve existing transactions, audit, receipts and public signatures. Propagate only permissions attached to asserted source role memberships.
- Implementation: Scoped Jena archive-level and sibling-name validation to project/shared/base schemas; reused one private level query in preflight and domain guards. Fixed grant propagation so orphaned annotations retained in revision snapshots cannot become active rights on new units (both backends). Added owned socket-only Redis/AOF fixture and real coordinated-write acceptance, documentation/results.
- Validation: 132 owned checks pass (115 previous plus 17 coordinated writes); 106 library tests plus 24 subtests and 11 API tests plus 13 subtests pass. Covers duplicate siblings, actual parent/mapping/grant RDF, orphan exclusion, atomic audit/receipt, exact retry/conflicting IDs, session journaling, full rollback/retry, stale apply and structure-only provenance. Redis validates appendonly/always/noeviction and real WAITAOF; process closed after run.
- Open: Complete inventory/media hydration and specialized queries, raw project transfer/export, real object-cache behavior and normal-adapter crash/uncertain-outcome recovery.
- Risks/Assumptions: Synthetic owned resources, ordinary writer with explicit ADMIN_CREATE and role/data rights; normal policy loader and coordinator, only object-cache I/O suppressed. Confirmed commit/abort evidence is not crash/failover acceptance. User Redis untouched; no public signature change, deployment, commit or push.

### Update 2026-10-28 22:39
- Decisions: Migrate inventory/adoption read queries and canonical folder snapshots; preserve public signatures, creator/role semantics, distinct counts and stale-review guards. Select only project/shared/base schemas for Jena hierarchy paths.
- Implementation: Added three private query-building methods to ArchiveRepository for RDF 1.2 grants, schema dataset and exact/subclass matching; used by inventory/adoption/snapshots. Jena adoption visibility now uses direct subject-bound joins after the old correlated EXISTS/UNION shape admitted restricted/orphaned identities. Added offline dialect/routing tests and owned real-query/model/preflight/cursor acceptance; documented results and boundaries.
- Validation: 115 owned checks pass (102 earlier plus 13 archive reads), 62 library tests plus 21 subtests, 11 API tests plus 13 subtests. Covers schema scope/cross-schema ancestry, exact unknown classes, mixed keyset/counts, hidden/disconnected folders, hidden targets, fresh receipt-hint authorization, stale plans/cursors and transactional revisions. Existing RDFLib fixture emits deprecation warnings.
- Open: Coordinated staging/adoption writes, structural audit/receipts, complete inventory hydration/HTTP workflows, specialized media queries, raw project transfer and export jobs.
- Risks/Assumptions: Explicit fixture policy and imported owned RDF; real model/query/permission/transaction behavior. API staging creation correctly refused absent write coordination; no guard relaxed. Redis object-cache I/O suppressed. GraphDB tested offline only; no shared services, public signature changes, deployment, commit or push.

### Update 2026-10-28 22:26
- Decisions: Migrate archive publication as a bounded service workflow before inventory/adoption. Preserve public signatures, review/authorization rules and whole-command transactions; edit only the public role's permissions.
- Implementation: Added RDF 1.2 grant reads for publication/link reviews and explicit reifier writes for publication. Extended private cleanup helper with optional target; preserve internal grants and unrelated annotations. Shared reifiers raise existing PublicationConflict. Added Jena/offline publication tests, owned real-service acceptance and documentation/results.
- Validation: 102 owned integration checks pass (91 previous plus 11 publication/link checks); 50 library tests plus 14 subtests and 15 API route tests plus 13 subtests pass. Covers stale ACL review, rollback after first-resource write, no failed receipt, exact replay/conflicting IDs, internal grant/metadata preservation, additive links, restricted republishing and fresh publisher membership. Initial incomplete fixture property definition corrected through common base model.
- Open: Archive inventory/adoption/repository snapshots, complete policy-file/HTTP publication acceptance with coordination, raw project transfer and export jobs.
- Risks/Assumptions: Publication fixture supplies explicit server policy while using real authorization/model/query/transaction implementations. Redis object-cache I/O remains suppressed. GraphDB regressions offline only; no public signature change, shared service change, deployment, commit or push.

### Update 2026-10-28 22:20
- Decisions: Port the concrete all_resources bulk-query gap while preserving public signatures, exact asserted-class matching, role-only authorization and existing joined-row pagination. Track specialized workflows separately.
- Implementation: Added backend-selected RDF 1.2 permission annotation to all_resources; documented its contract and fixed undefined project name in error logging. Added offline dialect/routing/result/error tests, owned bulk acceptance and copy/export call-path inventory with retained results.
- Validation: 91 owned normal API/Fuseki checks pass (85 existing plus 6 bulk checks); 21 targeted library tests pass. Verifies projection/missing values, count/page, threshold, orphan/foreign-graph isolation and transaction/abort visibility. GraphDB syntax covered offline only.
- Open: Complete tools staging command, specialized archive/media queries, raw GraphDB project dump/restore, complete export jobs and legacy native fulltext search. Joined-row pagination can truncate multi-valued projections; unchanged in this compatibility step.
- Risks/Assumptions: Synthetic owned data; Redis object-cache I/O suppressed. No public signature change, shared service modification, deployment, commit or push.

### Update 2026-10-28 22:14
- Decisions: Verify normal API resource-to-index behavior before expanding migration scope. Keep authorization in current RDF checks and field meanings bound to managed revisions; no new application abstraction needed.
- Implementation: Added check_fulltext_writes to the owned API acceptance runner, exercising real writes/search and dynamic model/field configuration. Added retained results and updated migration status documentation. Application code unchanged.
- Validation: 85 owned API/Fuseki checks pass, including previous 69; 27 library fulltext/connection tests and 13 API fulltext tests pass. Covers commit/abort visibility, counts/pagination, ACL downgrade/restoration, late field activation, AND/projection, stale revisions, remapping and delete cleanup. First run caught untyped values in the test's direct library assignment; corrected to existing QName/DataPermission contract.
- Open: Bulk/copy/export RDF-star paths, specialized archive/media workflows, operational cache/load and normal-API restart recovery acceptance.
- Risks/Assumptions: Synthetic owned data, ordinary-user search and isolated service; only object-cache Redis I/O suppressed. No shared service change, public signature change, deployment, commit or push. Prior isolated crash/restart evidence is separate from this normal-API run.

### Update 2026-10-28 22:07
- Decisions: Preserve resource-operation transaction ownership and public signatures. Share RDF 1.2 permission generation/cleanup across users and resources with explicit graph scope; keep GraphDB branches and existing creator/role semantics.
- Implementation: Ported resource permission checks, create, role-map updates, class transformation grants and deletion. Renamed internal user helper to jena_permission_write and added graph selection/object grant predicate. Shared-reifier checks precede writes; API delete maps inconsistencies to 409. Added owned resource acceptance, offline dialect/routing tests and documentation/results.
- Validation: 69 owned API/Fuseki checks pass (including previous 52), plus 78 library tests with 14 subtests and 35 API tests. Covers non-admin permission thresholds, duplicate create, stale update, update/delete callback rollback, composed-create rollback, transformation, grant revocation, shared reifiers and foreign-graph isolation. Initial failures exposed missing numeric permissions and root role in the synthetic fixture; fixture corrected without altering access semantics.
- Open: Remaining RDF-star bulk/copy/export queries, specialized dating/list/media/archive writes and linked transforms, normal-adapter fulltext mutation/search acceptance, deployment/cache/recovery gates.
- Risks/Assumptions: Only ordinary modeled resources/basic transformation accepted here. factory.read retains role-based access even for admin/creator; read_data/class read preserve creator access. Object cache I/O mocked in owned runner; no live GraphDB regression, shared services, commit/push or deployment.

### Update 2026-10-28 21:56
- Decisions: Port user membership annotations explicitly, without rewriting arbitrary SPARQL. Replace only changed project/role maps in the existing optimistic transaction; retain bare memberships and current authorization/authVersion behavior. Reifiers must describe one membership for permission edits.
- Implementation: Added jena_user_write helpers and opt-in connection capability; User serialization/update/delete handles RDF 1.2 grants, duplicate cleanup and unrelated metadata preservation. Shared-reifier preflight runs inside the transaction; API reports its conflict as 409 with OpenAPI documentation. Removed raw user-update query printing on failure. Added normal-API user/role acceptance and GraphDB serialization regressions.
- Validation: 52 owned API/Fuseki integration checks pass (including the previous 33); 66 library tests with 9 subtests and 29 API tests pass. Covers role CRUD, user CRUD/login, grant replacement/removal, authVersion, invalid target rollback, stale edits, missing rights, shared-reifier refusal and graph isolation.
- Open: Resource-instance RDF-star write paths, extended user-class properties, refresh-cookie revocation acceptance on the normal adapter, remaining list/search/service operational gates.
- Risks/Assumptions: Whole changed membership maps are replaced after the timestamp check; reifier identifiers are internal and can change. Unrelated reifier annotations remain historical metadata without permissions. Cache Redis I/O is mocked only in the owned runner. No live GraphDB test, shared service change, commit, push or deployment.

### Update 2026-10-28 21:46
- Decisions: Select Jena explicitly through OLDAP_BACKEND; retain GraphDB default and existing public signatures. Reuse credential/JWT logic; keep the private identity callback database-free. Never replay updates after uncertain replies.
- Implementation: Added JenaConnection, central API backend selection/validation, identity endpoint and Jena health check; User.read uses a private backend query hook. Real API acceptance exposed and fixed duplicate list BEGIN, implicit default-graph reads, wrong index predicates and ancestor-move interval calculation. Invalid descendant moves abort. Added configuration/acceptance documentation and retained result artifact.
- Validation: 33 owned API/Fuseki checks pass without connection mocks: startup/login/refresh, model/property/list CRUD and moves with index/position assertions, fulltext activation, real tools import/update/TriG+fulltext backup/dump and zero-write replay. 63 library tests (9 subtests), 29 API tests and 76 tools tests (3 subtests) pass. Initial owned failing runs reproduced list defects before correction.
- Open: Remaining user/role/resource RDF-star writers, normal-adapter search acceptance, multi-node/concurrent list moves, isolated Redis/cache operational acceptance and production service packaging/recovery.
- Risks/Assumptions: Only object-cache Redis I/O mocked in owned integration. No live GraphDB regression for shared list corrections. Jena service still uses migration session protocol; maintenance operations explicitly unsupported. No shared service/data/environment switch, deployment, commit or push.

### Update 2026-10-28 21:26
- Decisions: Bind managed fulltext administration to the authenticated connection, never to a separately selected dataset. Check fresh project metadata and active-user model/root administration on every request; preserve existing routes and defaults.
- Implementation: Added GET/PUT /admin/fulltext/<project>, no-store/error mapping, factory registration and OpenAPI contracts. Sibling library validates/authorizes; tools add explicit preflight/apply, snapshot state and portable dump.
- Validation: 21 API tests pass; 46 owned Fuseki checks execute real route, Project.read and fresh RDF authorization (factory/cache I/O replaced). 76 tools tests plus three subtests pass, including zero-mutation preflight failures and dump/load parity.
- Open: Normal API Jena transport/startup and model/list mutation acceptance. Provision projects before fulltext import. Authorization is request-boundary, not atomic with index publication.
- Risks/Assumptions: Default GraphDB Connection returns 503. Failed final activation leaves earlier model transactions committed, clearly reported; no replay. Synthetic URN project fixture exposed existing QName interpretation, replaced by HTTP IRI; general URN support not claimed. No service switch, deployment or data changes.

### Update 2026-10-27 22:40
- Decisions: Preserve HTTP API contracts and public oldaplib signatures and semantics throughout migration; internal transport/helper changes are preferred.
- Implementation: Recorded compatibility acceptance criteria and mandatory documentation/discussion for unavoidable public exceptions, including harvester and oldap-tools caller mapping.
- Open: Apply criteria to the revocation pilot and composed transaction/callback design.
- Risks/Assumptions: One-request optimization must not silently weaken transaction-local reads or callbacks. Documentation only; no application or external-consumer changes.

### Update 2026-10-27 22:36
- Decisions: Prefer one atomic mutation request per business operation; distinguish stock SPARQL Update from a server command with assertions/results. Keep dynamic Python/callback migration explicit; no generic session or workflow framework introduced.
- Implementation: Added AST inventory utility, source-hashed call-site snapshot and per-boundary migration table; analyzed real revocation, resource-hook, list, job and external-consumer flows. Extended isolated Fuseki probes for conditional batching.
- Validation: Parsed 620 Python files in eight repositories; 86 unique boundary-function rows (including infrastructure and operational probes), all snapshot-linked. All 27 capability/batch checks passed; stale-guard no-op hazard and guarded concurrent one-winner behaviour reproduced. Syntax/diff checks passed; test servers stopped.
- Open: Implement bounded revocation pilot with conflict/replay outcomes, then resource+audit+outbox and list/harvester composition. Existing double-start in list move and model-edit boundary need explicit treatment. Commit/push pending.
- Risks/Assumptions: Static syntax inventory cannot prove arbitrary downstream/dynamic callers. Synthetic receipts lack production request-digest semantics. No OLDAP application code, real data, Redis or service configuration changed.

### Update 2026-10-27 22:18
- Decisions: Keep the first Jena step isolated and synthetic. Explicit RDF 1.2 reifier identity is the working direction; defer transaction architecture selection until a real operation is mapped.
- Implementation: Installed checksum-verified Fuseki 6.2.0 outside Git using existing Java 25.0.2. Added reproducible Java TDB2 and Python-owned Fuseki HTTP probes plus report/results at ../oldaplib/docs/migration/j0-capability-probe.md.
- Validation: Final run passed 21 runner checks (including four Java transaction check groups). Covered read-own-writes, concurrent isolation/claims, rollback, request atomicity, restart persistence, all three grant patterns, revocation, graph scope, repeated insertion and Turtle round trip. No listener remains on test port 3031; syntax/diff checks pass.
- Open: Choose server-command versus multi-request transaction extension; test actual OLDAP workflows, failure recovery, inference and full text. Commit/push pending.
- Risks/Assumptions: Initial harness expected 404 but observed unsupported-route 405; corrected and rerun. Persistence tests use graceful restart, not crash injection. Anonymous annotation shorthand changes identity semantics. No OLDAP services or data changed.

### Update 2026-10-27 22:11
- Decisions: Treat SHACL only as model description/read metadata, per user clarification. Prioritize multi-request transaction feasibility and RDF 1.2 grant identity before backend implementation.
- Implementation: Added source-backed migration assessment at ../oldaplib/docs/migration/jena-assessment.md, covering transactions/recovery, RDF-star conversion, inference/graph scope, full text and model round trips; recorded phased acceptance gates and primary sources.
- Validation: Inspected both repositories and setup templates; local RDFLib 7.6.0 default Turtle parser rejected legacy RDF-star and RDF 1.2 triple-term probes. No Fuseki runtime or live database test performed.
- Open: Pin/install Jena and prove transaction and annotation contracts; choose transaction architecture, reifier identity and inference/search configuration.
- Risks/Assumptions: Standard remote SPARQL calls do not preserve existing interactive transaction semantics; runtime GraphDB ruleset not verified. No application code, data or services changed by this assessment.

### Update 2026-10-27 12:10
- Decisions: Use a separate authenticated native Redis on 127.0.0.1:6381; cache DB 0 and writer DB 1 share AOF/fsync-always/noeviction. No autostart installed.
- Implementation: Created private runtime configuration/data and ignored Redis-only .env.local. Updated native run targets to respect OLDAP_REDIS_URL. Added local lifecycle documentation.
- Validation: Authenticated PING, unauthenticated rejection, DB isolation, WAITAOF and persistence across restart passed; probe removed. Existing Redis PIDs unchanged; git diff check passed.
- Open: Fuseki, API endpoint/authentication configuration and isolated startup; commit/push pending.
- Risks/Assumptions: Existing service-control/test targets still refer to original OLDAP; do not use them for Jena. Redis setup alone does not establish backend compatibility.

### Update 2026-10-27 12:07
- Decisions: Isolate Jena development in sibling worktrees with Python 3.13 environments; use current ontology development as the library baseline.
- Implementation: Fast-forwarded the library migration branch from 0.4.27 to existing 0.7.29 history. Configured the API's editable sibling-library dependency and documented environment setup; retained PyCharm's in-project virtualenv setting.
- Validation: Poetry installation and lock checks passed in both Python 3.13 environments; API import resolves to the sibling migration library (0.7.29). API metadata deprecation warnings remain.
- Open: Separate Fuseki/Redis configuration, API ports and migration compatibility assessment; commit/push environment changes.
- Risks/Assumptions: Local path dependency is for migration development, not distributable releases. No services started or existing database configuration changed.

### Update 2026-10-26 00:50
- Decisions: Make structured Dating opt-in via Accept so existing clients retain legacy response shapes.
- Implementation: Updated OpenAPI DatingValue response contract. Shared serializer retains precision/calendar/verbatim uncertainty; search expands only requested Dating fields with reader-authorized batches of 100. Ten focused serialization/read/search tests pass, including legacy defaults, batching and unreadable omission. Restarted local API; live search and detail return full dates and uncertainty.
- Open: Publish/deploy API with matching FasnachtsPage and harvester changes.
- Risks/Assumptions: No ontology/oldaplib changes. Search expansion adds summary reads only for opted-in requested dates; existing /admin serialization is unchanged.

### Update 2026-10-20 12:32
- Decisions: Adopt AGPL-3.0-only for oldap-api as approved by the user.
- Implementation: Added official GNU AGPL v3 LICENSE, Poetry license metadata, README license scope and stable project context.
- Open: Commit and publication remain outside this change.
- Risks/Assumptions: User authorizes licensing the project; third-party dependencies retain their own terms. No runtime behavior changes. Validation: poetry check --lock passed (metadata deprecation warnings); wheel build passed and includes LICENSE plus AGPL-3.0-only metadata.

### Update 2026-10-14 21:04
- Decisions: Preserve exact-ID resume safety; report missing container identities explicitly instead of silently selecting replacements.
- Implementation: Added container inventory preflight and a bounded, credential-free missing-ID diagnostic; two regressions cover refusal/state retention and successful exact-ID restore. Backed up the local resume journal, reconciled three verified Compose replacements under the control lock, and reconnected the two stopped workers to the replacement Compose network with their original aliases.
- Open: No commit or remote deployment performed; generic failures other than missing IDs still use the existing redacted diagnostic.
- Risks/Assumptions: Eight focused service tests pass. Local services-start completed after repair; no data/volumes deleted, containers recreated, or writer locks reset. Worker image versions were preserved.

### Update 2026-10-11 22:53
- Decisions: Map OldapErrorNotFound from both media lookup routes to the existing generic 404 response; retain all other exception/status behavior. No blanket treatment of HTTP 400 as missing media.
- Implementation: Added specific ID/IRI exception handlers and docstrings, documented the existing not-found contract in OpenAPI/master context, and added 10 isolated Flask regression cases for typed/empty not-found, validation errors, configuration failures and successful serialization.
- Open: Release/deploy the API to Home; no version bump, image build or service restart performed. Investigate the requested asset UUID separately: a matching local import-owned asset directory contains original/001.jpg and derived/master.tif; this does not establish its presence in Home GraphDB.
- Risks/Assumptions: 12 focused offline tests pass (including instance-read fast path); no database-mutating integration fixtures run. Focused Black, Poetry lock check and diff check pass; existing Poetry metadata deprecations remain. No media/GraphDB data modified.

### Update 2026-10-10 00:10
- Decisions: User role membership without a default data permission must not become an implicit object grant. Explicit object grants require a valid DataPermission; no permissions are invented or membership records changed.
- Implementation: Filter None defaults in ResourceInstanceFactory, allocate an independent default map per instance, and validate explicit constructor grants before conversion. Four offline regressions cover mixed/empty memberships, explicit grants and malformed/null inputs. Installed reviewed local 0.7.26 development wheel into the native API and used guarded make restart; writer gate released.
- Open: User upload retry is the final live acceptance. Publish a new oldaplib release before remote rollout; current local wheel differs from the published version. Mediahelper normalization deployment remains separate.
- Risks/Assumptions: 19 focused source tests and four installed-runtime regressions pass; installed objectfactory hash matches source. Poetry check and diff check pass. Previous installed package backed up under ~/.codex/backups/oldaplib-default-roles-20261010-001005. No stored data, memberships, grants, remote service or Docker container changed; no full live database test suite was run.

### Update 2026-10-07 23:45
- Decisions: Correct the structured-search result in oldaplib rather than filtering API response rows.
- Implementation: Activated the sibling library fix for OPTIONAL/unbound equality via local 0.7.25 development wheel and make restart; writer gate released normally. Verified results/counts for parent, missing, absence and boolean filters with sorting through installed runtime.
- Open: Publish new oldaplib version and update dependency lock before external rollout; see ../oldaplib/docs/search_optional_values.md.
- Risks/Assumptions: No API source, lockfile, stored data or remote deployment changed. Installed local development wheel differs from published 0.7.25.

### Update 2026-10-01 11:50
- Decisions: Accept user-deployed project-identity optimization on the VM; retain four workers/two threads.
- Implementation: Recorded deployed API 0.2.31 / oldaplib 0.7.25 source verification and read-only before/after evidence; updated context and relevant performance/worker documentation. No application code or deployment configuration changed.
- Validation: 1,152 timed reads pass; all 17 baseline contents and public HTTPS checks match. Resource medians improve 10–13%, summaries 4–10%. At 16 readers: median/p95 167/591→143/559 ms, API CPU 1.78→1.57 cores. Existing 50,396-binding RDF fingerprint, containers and service PIDs unchanged; temporary VM files removed.
- Open: Larger representative data and sustained mixed-user sizing remain separate; no worker maintenance indicated by this workload.
- Risks/Assumptions: One sequential short warm anonymous comparison, not maximum capacity. Search/fresh-model gains not demonstrated; recovery p95 varies upward. Separate final verifier excludes the completed load-client process; within-run service-process guard passed. Existing local changes preserved.

### Update 2026-10-01 00:43
- Decisions: Retain a small project-identity projection; avoid broader model caching or generic copy changes. Gains are useful but below a consistent 15–20% across all endpoints.
- Implementation: Added propertyclass.py to read-harness source hashes; documented two local source comparisons with JSON/CSV evidence and full-catalog equivalence. Production API behavior/configuration is unchanged.
- Validation: 75 library, 14 API and 19 tool checks pass; 1,000 accepted timed reads return 200; 34 before/after contents match. Anonymous medium improves 13–16%; summaries improve 6–13% across users/rounds. Full Project copies 524→181; 3 GraphDB/42 Redis reads unchanged. All accepted RDF fingerprints unchanged (52,490 bindings).
- Open: Normal library release/consumer dependency update, then read-only VM comparison with existing worker settings. No installation, restart, version bump or deployment performed.
- Risks/Assumptions: Warm sequential laptop measurements, not concurrent production capacity. First direct-copy prototype discarded and excluded due closing source-inventory mismatch; final accepted source inventories stable. Existing user changes preserved.

### Update 2026-10-01 00:27
- Decisions: Verify deployed source identity, then replay the exact prior VM full-batch catalog at unchanged four-worker/two-thread settings; exclude incomplete measurements from acceptance.
- Implementation: Fixed Docker sampling to identify Gunicorn/Java/Redis service processes instead of transient healthcheck/exec helpers; retain missing-service/PID-change failure and add expected/observed diagnostics. Added two regressions, updated measurement guide and published VM comparison JSON/CSV/report.
- Validation: 19 offline read-tool checks pass. API 0.2.30 / oldaplib 0.7.24 serializer hash matches accepted source. Complete rerun: 1,132 timed HTTP-200 reads, stable content, all 17 references match previous baseline, full 25/100 summary cardinalities. At 16 readers: 16.13→17.03 requests/s, median 232→167 ms, p95 649→591 ms, API CPU 2.13→1.78 cores. Public HTTPS reads pass; RDF fingerprint (50,396 bindings), containers and service PIDs unchanged; temporary VM directory removed.
- Open: Profile independent Project/model copying locally; retain current worker settings. Large-data/HMB sizing remains separate.
- Risks/Assumptions: First attempt stopped during final recovery because unfiltered process inventory changed; original service PIDs and logs show no worker replacement. Exact transient helper was not captured. Accepted rerun preserves query/timing logic. Short warm anonymous sequential comparison, not maximum capacity or an SLA. No RDF writes, cache flush, application change or service restart during tests.

### Update 2026-09-30 23:50
- Decisions: Attribute a single library CPU optimization against an explicit 0.7.23 baseline, keeping native and production deployments unchanged.
- Implementation: Added benchmark mode selection, imported source-version/serializer-hash inventory and normalized response hashes; test-only Gunicorn workers expose/verify serializer source identity. Published local A/B report, JSON/CSV and updated reproduction/context documentation. Existing VM measurement changes remain intact.
- Validation: 101 focused offline checks pass (70 library, 14 API, 17 tools). 640 timed serial/instrumented reads and 1,768 HTTP load reads return 200; all workload responses and 34 full-catalog before/after comparisons match. Resource median 90.8→66.5 ms; 16-reader throughput 13.98→16.91 requests/s and p95 796→568 ms. Fingerprints unchanged (52,490 bindings); temporary port released and native service PIDs preserved.
- Open: Publish updated oldaplib and update consumer environments through the usual workflow before VM remeasurement. Native API distribution on disk is still 0.7.22; source experiments intentionally bypass it.
- Risks/Assumptions: Warm sequential A/B, fixed data/workflows, one Gunicorn worker/four threads; not a VM capacity prediction. Normalized model-array ordering differs from native in the same four baseline/candidate cases. No existing GraphDB mutation, package install, service restart, cache flush or release.

### Update 2026-09-30 23:30
- Decisions: Validate the user's deployed API with bounded anonymous reads; preserve GraphDB, current workers and service configuration. Keep exact laptop-catalog replay separate from full VM metadata batches.
- Implementation: Added Linux/Docker read runner with exact request/body allowlist, disabled redirects/proxies, fixed SELECT fingerprints and process identity monitoring. Reused the existing workload engine through a snapshot callback; made dotenv a local-baseline-only import. Added safety tests and VM report/JSON/CSV.
- Validation: 17 offline read-tool tests pass. VM v0.2.29 / oldaplib 0.7.23: 2,409 timed HTTP-200 reads, normalized content stable; full batches at 16 readers: 16.13 requests/s, median 232 ms, p95 649 ms. Public HTTPS health plus three representative reads pass. All fingerprints retain 50,396 bindings; containers/PIDs unchanged; temporary VM directory removed.
- Open: Profile per-request model construction/deserialization/serialization; consider controlled worker comparison separately. No causal pre-deployment VM comparison or release-image write/recovery rehearsal performed.
- Risks/Assumptions: Warm fixed anonymous reads, short closed-loop stages and different VM/laptop data. Original summary IRIs return only 15/60 resources; supplemental VM catalog verifies full 25/100. CPU/RSS include background work; timings exclude WAN/proxy/browser. No GraphDB update, cache flush or service restart.

### Update 2026-09-30 23:10
- Decisions: Persist the API dependency lock in Git so the oldaplib release selection survives a fresh checkout.
- Implementation: Ran `poetry update oldaplib --lock`; the lock now resolves oldaplib 0.7.23. Removed `/poetry.lock` from `.gitignore` and documented the lock workflow.
- Validation: `poetry check --lock` passes with existing Poetry metadata deprecation warnings.
- Open: Commit/push the lock and documentation; deployment remains separate.
- Risks/Assumptions: The previous lock was untracked, so a complete before/after dependency diff is unavailable. No installed environment, running service or Docker image changed. Runtime Docker pip installation still resolves wheel dependencies independently.

### Update 2026-09-30 01:15
- Decisions: Keep the native laptop runtime unchanged and validate multi-worker recovery through the production-style Docker container boundary.
- Implementation: Linked Docker worker configuration/recovery documentation in oldap-setup and updated project context. Real current API sources are exercised by isolated test-only injection routes in setup; no production routes or recovery-library logic changed.
- Validation: Source-verified two/four-worker Docker recovery passes worker crash/replacement, durable blocking, container fencing, data preservation/rollback, fresh API startup and post-finish commit. Setup records 34 passing tests, syntax checks and JSON evidence.
- Open: Build/rehearse the release image and measure on the eight-vCPU Docker VM. Native single-process recovery remains intentionally unchanged.
- Risks/Assumptions: Synthetic fixture transactions test recovery infrastructure, not every resource business rule. No VM deployment or shared-data modification.

### Update 2026-09-30 00:50
- Decisions: Preserve shared cache across worker lifecycle, initialize process-local prefixes before readiness, and compare isolated read-only Gunicorn 1/2/4-worker deployments without changing the native service.
- Implementation: Added writer-gated explicit clear-object-cache CLI, race-safe directory creation, startup tests, alternate benchmark port/multi-PID metrics, supervised temporary service and read-only test hook. Updated maintenance/runtime context and reports with JSON/CSV/source hashes.
- Results: 2,830 matching HTTP-200 reads; at 16 readers, 1/2/4 workers achieve 14.46/18.26/19.35 requests/s and p95 783/443/306 ms. All seven tested workers pass cold bearer-token reads; RDF fingerprints unchanged. Test port released; native API/GraphDB process identities preserved.
- Validation: 22 offline API tests, 12 read-tool tests and three isolated-Redis restart tests pass. Serial four-worker preflight lacked listener coverage and stopped safely; parallel preflight fixed coverage and the four-worker stage was rerun. Restart fixture import requires source PYTHONPATH; no library installation changed.
- Open: Native writer recovery assumes one foreground process. Design/test process-group supervision, fencing and crash recovery before write-enabled multi-worker deployment; then compare 2/4 workers on the eight-vCPU VM with representative data.
- Risks/Assumptions: Short closed-loop hot-read stages; fixed four threads per worker and no GraphDB queue attribution. Startup now requires GraphDB/anonymous access; restart no longer invalidates cache. Explicit invalidation needs drained readers/writers and was not run on shared services. Existing native service loads changes only at a future restart.

### Update 2026-09-30 00:27
- Decisions: Measure mixed anonymous readers against the existing native service; prioritize a controlled multi-process API experiment from the results.
- Implementation: Added bounded live HTTP ramp/recovery harness, independent sessions, normalized content checks, read-only transport guard, process CPU/RSS sampling and explicit RDF fingerprint preservation. Added report, aggregate JSON/CSV and reproduction documentation.
- Results: 2,083 matching HTTP-200 reads across 1/2/4/8/16/1 readers; at 16, 14.19 requests/s, 1,074 ms request p95, API 98.1%/GraphDB 59.6%/Redis 1.4% of one core. GraphDB fingerprint unchanged; nine offline benchmark tests pass.
- Open: Remove unconditional per-worker cache clearing through an explicit invalidation lifecycle; verify cold-worker prefixes; compare Gunicorn 1/2/4 workers and then remaining model/serializer CPU work.
- Risks/Assumptions: Fixed hot reference data, closed-loop think time, one short ramp, anonymous access only, no GraphDB queue attribution or HMB sizing. Recovery p95 differs from initial p95. No application/library code, service configuration, deployment or data changed.

### Update 2026-09-29 23:47
- Decisions: Activate measured oldaplib cache/project-read improvements locally, preserving API contracts and GraphDB data; no production deployment or published release.
- Implementation: Installed unpublished optimized oldaplib wheel still versioned 0.7.22, backed up previous package/dist-info, and restarted native API through the existing writer gate. Added exact saved-catalog replay, anonymous process bootstrap outside timings, source hashes, and before/after JSON/CSV/report.
- Results: 1,188 successful timed reads; public medium 515 to 97 ms, 25 summaries 758 to 112 ms, 100 summaries 548 to 148 ms. Redis calls 563 to 42 per resource. Both 34-case content comparison sets match; explicit named-graph fingerprints unchanged.
- Open: Mixed-user load tests and later scale/Enterprise/framework decisions. Publish a normal versioned library release separately.
- Risks/Assumptions: Warm, serial, small local dataset; both optimizations measured together. Standard API restart cleared only the object cache before warmup. Redis pools are bounded to 32 connections per process/configuration. See doc/performance/2026-09-29-optimization.md for limits and rollback identity.
- Validation: 39 library/isolated writer-store tests, 10 API tests, and four benchmark tests pass; no destructive GraphDB test fixtures.

### Update 2026-09-29 23:30
- Decisions: Execute read-only performance steps 1–2 against the existing local deployment; unknown is the primary subject and authorized rosenth is a separate administrator comparison.
- Implementation: Added a bounded sequential benchmark and offline guard/timing tests under tools/, with actual runtime inventory, explicit named-graph fingerprints, live HTTP and isolated Flask measurements, nested library/transport spans, and separate CPU profiles. Documented reproduction and measurement limits in doc/performance/README.md.
- Results: Completed 1,188 timed HTTP-200 reads across baseline/supplement plus 34 matching live/isolated content comparisons. Explicit named-graph fingerprints unchanged. Resource reads show 563 cache hits, 524 Project.read calls and only three GraphDB queries; refined attribution identifies repeated Redis connection setup as the largest bucket. See doc/performance/2026-09-29-baseline.md and its CSV/JSON aggregates.
- Open: Prioritize Redis pool reuse and request-scoped model/project reuse in step 3; concurrency, data growth, Enterprise and FastAPI remain unmeasured.
- Validation: Four offline mutation-guard/method-wrapper/timing-accounting tests pass; no destructive integration suite.
- Risks/Assumptions: Shared warm caches may be populated normally; no flush, service restart, GraphDB mutation or installed library changes. GraphDB HTTP time includes transport and engine waiting/evaluation. Local Fasnacht data are not representative of HMB scale.

### Update 2026-09-27 23:08
- Decisions: Preserve existing deployments; add trusted server-owned mail destinations and opt-in SALSAH installation.
- Implementation: Added server-owned frontend mail routing with exact Origin selection, internal durable job IDs, fail-closed validation, and legacy fallback. See doc/frontend-mail-routing.md.
- Open: Publish immutable compatible releases; perform coordinated initial installation and real DNS/TLS/browser/SMTP acceptance.
- Risks/Assumptions: No server deployment or image publication performed. Initial configuration requires an API restart; frontend-only updates do not.
- Validation: 117 isolated API/security/auth/mail/import/export regression tests passed; no live GraphDB integration tests or SMTP delivery performed.

# CODEX_LOG

### Update 2026-09-22 23:26
- Decisions: Administrative model planning/export must read GraphDB freshly after out-of-band Workbench edits; never clear all Redis databases to repair model visibility.
- Implementation: API JSON model GET and TriG download now use DataModel.read(ignore_cache=True). OpenAPI documents fresh reads and corrects the download path spelling to match the existing route. Two regression cases simulate deleted graphs with a stale cached model; 14 targeted API/auth/connector tests pass. Safely restarted local API. Captured complete explicit RDF before/after snapshots at /Users/rosenth/.codex/backups/oldap-fasnacht-recovery-20260922-232248; restored only fasnacht onto/shacl from the user's 23:15 API ZIP after confirming zero differences against the exported YAML. Restoration held the normal writer gate and used additive RDF import with exact graph-scope validation.
- Open: User browser acceptance; publish the API fix through normal release workflow. Workbench edits to other cached entities still require appropriate scoped invalidation.
- Risks/Assumptions: The earlier same-state roundtrip did not test external graph deletion and overstated recovery confidence. Fresh administrative reads cost additional GraphDB queries. All 27 other graph contexts are RDF-isomorphic before/after, including all 25,435 Fasnacht data triples and taxonomies. Recovered API: 16 classes; YAML replace dry-run: zero operations; Lucene: 693 entities; ArchiveObject/ArchiveMediaObject API samples read successfully. Connector configuration/index was not replaced during recovery. No global cache flush, data-graph mutation, or production change.

### Update 2026-09-22 23:06
- Decisions: Preserve complete Lucene creation options in native YAML; load remains opt-in and project-scoped. Existing shorthand and transport defaults remain supported.
- Implementation: Register Lucene blueprint, request/revision validation and mapped errors; add route/authentication regressions and OpenAPI contract. Rename pre-existing colliding publication YAML anchors without changing their schemas; the complete OpenAPI document now parses. 126 tools tests + 8 legacy tests + 25 targeted library/API/export/auth tests passed. Live Fasnacht dump retained 16 classes, 10 taxonomies and all options of the 8-field connector; replace dry-run planned zero operations. No live connector/model writes.
- Open: Publish paired releases before use outside this local development setup; no release/version bump performed.
- Risks/Assumptions: Connector commands are not RDF transactions. Failed replacement attempts restoration but may require reindexing; administrators outside configured writer coordination must serialize changes. Installed a local, unpublished oldaplib wheel still labelled 0.7.21 in the native API Python 3.13 environment; activated with writer-gated make restart. Production unchanged.

### Update 2026-09-18 23:47
- Decisions: Document the additive automatic editorial-default capability.
- Implementation: Add optional automaticEditorialGrants to PublicationCapabilities in OpenAPI; response is supplied by the updated oldaplib. No route, request or CaptureApp contract changes.
- Open: Update the normal oldaplib dependency after its release, then restart/deploy API.
- Risks/Assumptions: Absent capability on older libraries deliberately blocks the new frontend shared-assignment flow. No production or local service changes.

### Update 2026-09-17 23:57
- Decisions: Provide project-neutral placement summaries as a bounded read-only API rather than per-item frontend lookups.
- Implementation: POST /archive/{project}/placement-status accepts up to 500 targets; one COUNT(DISTINCT) aggregate per batch with separate target/media ACL filters. Policy supplies classes/semantic relation. Hidden destinations count as assigned without revealing identities. OpenAPI and doc/archive-placement-status.md document the contract.
- Open: Release/deploy API before the updated FasnachtsPage. Existing publication policy is required; no oldaplib release or migration.
- Risks/Assumptions: Advisory snapshot only, no writer lock or mutation; existing write guards remain authoritative. Nine unit/HTTP tests and real GraphDB rollback fixture verify partial/full/empty/direct media, hidden media/targets and hidden destinations. Local API restarted via guarded Make target; no lock reset or production writes.

### Update 2026-09-16 23:36
- Decisions: Provision reserved staging folders through an explicit generic administrative command, independent of organisation-role visibility. No ontology or CaptureApp contract change.
- Implementation: POST /data/{project}/staging-system-folders checks fresh ADMIN_RESOURCES/system ADMIN_OLDAP, locks and atomically fills missing top/Trash/Mobile with existing ACL conventions and audit. Rejects ambiguous topology, preserves existing resources, returns only readiness. OpenAPI and doc/staging-provisioning.md describe deployment and bounded direct writes.
- Open: Release/deploy this API before the updated FasnachtsPage.
- Risks/Assumptions: Area creation remains a separate resumable request. No additional private role/read grants. 53 focused tests passed; real local GraphDB create/retry probe rolled back entirely. Local API restarted safely. New OpenAPI block parses; full-file PyYAML validation encounters duplicate anchors already present in HEAD.

### Update 2026-09-14 23:10
- Decisions: Return local API to the published oldaplib dependency through normal Poetry resolution.
- Implementation: `poetry update oldaplib` confirmed no further update needed: lock and installed package already resolve 0.7.20. Verified site-packages import, no direct/local-wheel origin metadata, and direct media count implementation. `make restart` passed API readiness and released the writer gate.
- Open: Production deployment remains separate.
- Risks/Assumptions: No dependency constraint, archive data, permissions or production services changed. Existing staged user changes preserved.

### Update 2026-09-14 22:50
- Decisions: Add generic permission-filtered direct media counts to folder-default proposals; use one aggregate query, never per-folder media reads. Counts are display-only and excluded from review hashes.
- Implementation: oldaplib COUNT(DISTINCT media) covers same-area staging media and configured archive references. Optional directMediaCount documented in shared JSON schema/OpenAPI; regenerated FP types; shared UI consumes counts with older-server fallback. 28 backend tests and browser count/recovery smoke pass. Local GraphDB: 46 folders/125 visible placements, 7–30 ms aggregation; three inventory comparisons agree. API HTTP 200 verified after safe restart (cold proposal 21.6 s, warm 1.86 s for sampled folder).
- Open: Normal version bumps/publication and consumer updates before production. Existing frontend/library check baselines remain; no ontology changes.
- Risks/Assumptions: Local API uses a development wheel still labelled 0.7.19, ahead of published 0.7.19; do not deploy that version as if released. Backup: BACKUP/local-media-counts-20260914-224638/installed-oldaplib.tar.gz. No archive data, role or production writes. Zero means no visible direct media, not proof of global emptiness.

### Update 2026-09-13 23:18
- Decisions: Activate publication on the local MacBook first; production remains unchanged. API-only media workers do not require an independent archive policy or Redis gate.
- Implementation: Verified installed oldaplib 0.7.19; replaced three local media containers using old :local/0.7.11 with v0.2.12/0.7.19, persisted Compose tag and backed up configuration. Validated/atomically added local publication policy and safely restarted native API under writer gate. Installed-library GraphDB success/retry/receipt and failure rollback pass; API capabilities 200, unauthenticated 401, authorized IIIF 200/unauthorized 401. BMG-Archivist publisher membership verified read-only.
- Open: User authenticated UI acceptance; separately coordinated production activation. Public archive viewer token propagation remains separate.
- Risks/Assumptions: No existing RDF resource, role assignment or public grant changed; fixtures/receipts rolled back. Backups in BACKUP/local-publication-20260913-231358 and local-publication-policy-20260913-231513.json. No CaptureApp, production, version or Git publication changes.

### Update 2026-09-13 00:58
- Decisions: Expose publication as narrow project-neutral endpoints, preserving generic and CaptureApp contracts.
- Implementation: Added authenticated no-store capabilities/preview/apply/owner receipt routes, OpenAPI closed schemas, lazy versioned service resolution and route/non-disclosure tests. Validation: 85 focused backend/gate tests and 4 frontend retry tests pass; local GraphDB success/replay and injected-failure rollback pass. Both frontend builds/lint pass; FP check baseline unchanged (23/37), SALSAH check clean.
- Open: Matching oldaplib release and all-writer deployment before publication policy activation.
- Risks/Assumptions: No production or local shared policy activation; new endpoints fail closed without matching library/configuration.

### Update 2026-09-11 02:39
- Decisions: Align archive data endpoint project converters with the existing generic instance routes to avoid Werkzeug dispatch collisions.
- Implementation: Inventory GET and reference-move POST now use path:project; public URLs and payloads remain unchanged. Added full-factory route regression coverage for short/absolute project identifiers, ordinary resource reads, and authentication. All 14 route/archive view tests pass.
- Open: Publish and deploy an API patch release, then repeat the production BMG-Archivist workspace acceptance check.
- Risks/Assumptions: No data, permissions, frontend, or CaptureApp changes. Blueprint-only tests had missed this collision; the complete route map reproduces and verifies the fix. Production remains on the previous image until deployment.

### Update 2026-09-10 19:32
- Decisions: Implement a separate folder-default tree; suggestions require a unique recorded structure-only origin and current target visibility. Save/remove one folder at a time, without changing media or archive structure.
- Implementation: Added default_proposal/read-only API route and generated client, shared source-choice loader, and ArchiveFolderDefaults below persisted management. Preflight/apply remains authoritative and exact pending requests survive reload. 28 backend/API tests plus 21 subtests, targeted lint, build, defaults desktop/mobile retry smoke and step-one/public regression pass; check baseline remains 23 errors/37 warnings in 15 files. Guarded API restart succeeded; live read-only response returned 44 folders/seven hints.
- Open: User acceptance; SALSAH-2 UI adaptation remains separate.
- Risks/Assumptions: Hints suppressed above 1,000 scanned receipts, capped at 500 with warnings. No guessed names/recency, ontology/Capture changes, live default writes, commit or production deployment. Existing unrelated changes preserved.

### Update 2026-09-10 19:12
- Decisions: Separate creating empty archive units from hierarchy editing and folder defaults. Keep old request semantics and exact uncertain retries compatible.
- Implementation: Added optional applyMappings=false in library/API/client contracts, suppressing folder writes while preserving creation grants and storing origin IDs in private receipts. Replaced the combined FasnachtsPage editor with a fixed-hierarchy source/placement/name/level/review flow. 26 backend/API tests plus 15 subtests, targeted lint, build and desktop/mobile/public fixture smoke pass; frontend baseline stays 23 errors/37 warnings. Local API restarted through its guarded Make target; live read-only preflight confirmed zero default changes.
- Open: Step-three default editor and retrieval of recorded provenance; user acceptance of step one. New operation IDs are separate imports, not cross-operation deduplication.
- Risks/Assumptions: No ontology/Capture changes or live archive writes; old SALSAH requests retain combined behavior. Match API/library release before deploying the new frontend. No commit/push or production deployment; unrelated work preserved.

### Update 2026-09-10 12:36
- Decisions: Include all Docker Desktop workloads and the four native backend/store jobs; keep frontends and unrelated native apps manual, as explicitly selected.
- Implementation: Added documented services-stop/start/status targets and development_services.py; shared reviewed environment validation with restart_api.py. Stop uses writer exclusion, persistent native disable and exact Docker resume IDs; all engine calls pin the local socket. Docker status handles a fully exited Desktop without hanging. Verification: nine focused tests and the full live stop/start cycle pass; repeated stop is safe, native jobs stay disabled while stopped, all six original containers return, and the writer gate is free afterwards.
- Open: No change to Docker login-item preferences or audio-system configuration.
- Risks/Assumptions: Finish transfers first; occupied writer gates refuse stop. Partial failures preserve resume/safety state; no stale-owner reset, volumes removed, commit or production changes.

### Update 2026-09-10 12:22
- Decisions: Keep native API development restart accessible through Make; preserve retained-owner recovery rules.
- Implementation: Added documented `make restart` and help entry, backed by restart_api.py: validated local inventory/environment, atomic writer exclusion, kernel exit/job removal and API readiness checks. Added three isolated Redis tests; actual make restart succeeded without restarting GraphDB/Redis.
- Open: None for this local development target.
- Risks/Assumptions: Occupied writer/recovery gates refuse restart; uncertain runtime control retains the gate. Existing unrelated working changes preserved; no commit or production changes.

### Update 2026-09-10 12:10
- Decisions: Complete WR-04 local operational acceptance; enable only the explicitly authorized rosenth operator. Production remains a separate target-specific rollout.
- Implementation: Verified real API authorization/no-store/free state and actual Redis evidence-denial ACL; enabled private local runtime configuration and dedicated operator role through ordinary OLDAP models. Local SALSAH CORS origin localhost:5175 was added and verified against the actual API. Acceptance: 50 recovery/native, 19 deployment, 49 authentication/Capture transport and 8 frontend tests pass; 10 native and 15 pinned Redis checks pass. Both live/fixture UI flows and builds pass; FP typecheck baseline remains 23 errors/37 warnings, SALSAH is clean.
- Open: Production multi-host/SSH partition, whole-host reboot and independent-storage restore acceptance; native Capture acceptance retains the user's local waiver.
- Risks/Assumptions: Native services must remain foreground and within the reviewed inventory; unmanaged direct writers are maintenance-only. Persistent controller/gate state never expires. No commit, push or production deployment.

### Update 2026-09-10 01:32
- Decisions: Expose additive deployment-wide recovery endpoints with fresh operational authorization and sanitized closed responses; never accept runtime/evidence claims from HTTP.
- Implementation: Registered writer-recovery blueprint for capabilities/status/begin/operation/finish; closed 8-KiB inputs, canonical UUID/revision/reason validation, no-store responses, scoped Redis pool cleanup, bounded fresh role query and explicit unknown-result handling. Added OpenAPI schemas and real isolated-Redis HTTP tests.
- Open: Recovery activation remains disabled; WR-04 target/runtime acceptance and native MacBook control are still required. No role assignment or deployment.
- Risks/Assumptions: 44 recovery/library/service tests plus eight existing authentication tests pass. Live unauthenticated discovery returns 401/no-store. Both clients validated against the same HTTP contract. No Capture transport/source changes.

### Update 2026-09-10 01:05
- Decisions: Use a deployment-wide ordinary operational role with authoritative membership checks, independent of archive editing and administrator shortcuts.
- Implementation: Added WriterRecoveryService for diagnosis, begin/status/finish and actor binding; every call queries current active-user role membership. Dedicated recovery Redis credential and reviewed runtime inventory digest are opt-in. Added four unit tests and service integration documentation.
- Open: WR-03 authenticated no-store HTTP contracts plus FasnachtsPage/SALSAH-2; WR-04 native runtime/target acceptance. No role assignment or recovery activation.
- Risks/Assumptions: 51 combined library/API focused tests pass. No existing API/Capture contract, route, ontology or source change in CaptureApp. No Docker socket or shell capability enters the API.

### Update 2026-09-09 23:19
- Decisions: Honor the configured durable writer store and normalize export identity values at the OLDAP search boundary.
- Implementation: Makefile run/run-prod preserve OLDAP_STAGING_LOCK_REDIS_URL from local settings. Archive export reader expands typed QName subjects/links before selection and manifest joins while preserving literals; added regression. Deployed current editable API/library locally with enabled project policy and dedicated AOF Redis 6380/1.
- Open: Versioned production deployment and native Capture acceptance remain separate; no Capture contract/source changes.
- Risks/Assumptions: 37 export tests pass. Actual BMG estimate returns 256 files/499433768 bytes; editor/unknown capabilities and canonical reads pass. Media services restarted. No production or git publication.

### Update 2026-09-09 21:57
- Decisions: Keep API and Capture contracts unchanged for user-approved project creation grants implemented in matching oldaplib.
- Implementation: Documented optional grantEditorRolesOnCreation and library deployment ordering; updated stable context. Archive HTTP boundary/structure unit tests pass in the 90-test combined suite; Capture contract probe passes with synthetic transport.
- Open: Matching library deployment, reviewed policy/resource migration, durable gate and native/target acceptance.
- Risks/Assumptions: API application code/routes/payload schemas unchanged; documentation only in this repository. No runtime activation or CaptureApp source changes.

### Update 2026-09-08 16:20
- Decisions: Resolve the archive/mobile lifecycle merge by retaining both sides: coordinated archive checks and resource callbacks/outbox, legacy receipt normalization and all typed error mappings. Preserve existing Capture contracts.
- Implementation: Combined update/delete and OpenAPI conflicts; retained 84 routes and validated 812 refs without duplicate keys. Added guard-before-hook note/clear regression; corrected the incoming test double's required property model. 236 API tests plus 22 subtests, actual isolated lifecycle/adoption and Capture transport/parser checks pass. Documentation: doc/archive_mobile_merge.md.
- Open: Merge is resolved and staged for review/commit; native AS-T12 and target acceptance, matched dependency releases/lock and activation remain separate.
- Risks/Assumptions: Matching oldaplib hook/archive integration rechecked after Tower reset and still intact. No CaptureApp, production data, runtime configuration or service changes. Existing unrelated regex warnings retained; merge remains uncommitted for review.

### Update 2026-09-08 12:08
- Decisions: AS-05 reuses manifest/metadata v1 and existing public APIs; count originals per private path and retain the five-minute capability lifetime.
- Implementation: Added permission-checked catalogue references, deduplicated source resolution, per-placement totals/CSV kinds, frozen path/membership/source reauthorization; authoritative RDF deletion now precedes binary withdrawal. Verified 141 API tests, 281 media tests (one Linux-only skip), isolated GraphDB/real-writer integration, and network-disabled Docker deletion smoke; Black/Poetry/diff checks pass. Updated an older Staging test double to expose its required property model.
- Open: Verification complete; evidence is recorded in FasnachtsPage docs/as-05; AS-06–AS-09 UI, SALSAH, native acceptance and operational rollout remain separate.
- Risks/Assumptions: Already issued links remain valid for at most five minutes; uncertain DELETE outcomes retain originals for reconciliation. No ontology, CaptureApp, application RDF, policy activation, secret or deployment changes; existing uncommitted work preserved.

### Update 2026-09-08 00:08
- Decisions: Complete AS-04 source work with frozen wire contracts, source-scoped grants and unchanged guarded CRUD; AS-05 mixed ZIP export is next.
- Implementation: Added reviewed adoption/API/schema/docs and correlated receipts/audit; eliminated repeated vocabulary/ACL/QName validation and redundant read aggregation. 174 focused tests plus 42 subtests, all 61 ObjectFactory tests and real adoption/lifecycle/HTTP/concurrency/rollback/deletion regressions pass; 500 actions commit in 55.733 seconds. Build, OpenAPI/schema checks and final wheel verification pass. Evidence: FasnachtsPage docs/as-04.
- Open: AS-05–AS-09 export, admin UI, SALSAH, native Capture acceptance, production ACL/coordination migration and activation. Production depth/contention/latency acceptance remains necessary.
- Risks/Assumptions: With explicit user approval, backed up GraphDB Desktop cfg and changed heap from automatic 9 GiB to explicit 12 GiB, then restarted/verified service. No API timeout change, live RDF/ontology/role/policy change, CaptureApp edit or deployment. All disposable test repositories/caches removed; previous unrelated working changes preserved.

### Update 2026-09-07 23:42
- Decisions: Implement AS-04 reviewed structure adoption with project-neutral backend and no ontology/CaptureApp changes; retain all pre-existing work.
- Implementation: Added frozen proposal/preflight/apply bindings and adoption receipt response, strict body limits, HTTP tests, OpenAPI schemas and guide; legacy Capture and YAML shapes remain unchanged.
- Open: Complete isolated maximum-envelope and full ObjectFactory/lifecycle regression verification before marking AS-04 complete; subsequent export/UI/SALSAH/activation remain later steps.
- Risks/Assumptions: Local GraphDB at 9 GiB heap encountered free-heap guards/interrupted queries during large tests. User explicitly approved increasing to 12 GiB and clean restart; configuration backed up. No application RDF, role, policy or deployment change. The permission-query simplification still needs full real regression verification.

### Update 2026-09-07 22:59
- Decisions: Keep legacy transform/Capture bodies and response identities unchanged; expose mixed repository inventory through the frozen additive GET binding.
- Implementation: Added staging-folder-inventory route with strict query inputs, purpose-derived cursor key, no-store errors and OpenAPI schemas; extended HTTP tests/documentation. Matching oldaplib atomically retains references/read grants and resolves stale source retries. 76 mobile/StagingArea regressions and the parent 187-test focused set pass; real HTTP note/transform and mobile receipt replay after relocation verified.
- Open: AS-04 and later UI/export/SALSAH integration, native Capture acceptance, reviewed ACL migration and deployment.
- Risks/Assumptions: Requires accompanying oldaplib changes and opt-in durable coordination. Signing-secret rotation invalidates cursors. CaptureApp and existing runtime/ontology/role data were not changed.

### Update 2026-09-07 22:23
- Decisions: Complete AS-02 HTTP bindings with unchanged legacy/Capture formats and frozen additive v1 contracts; post-catalogue note writes/clears always receive the agreed 409, including combined/admin roles.
- Implementation: Registered capabilities/reference-move/receipt routes, schema/OpenAPI documentation and typed no-store errors. Update conversion now follows the coordinated fresh lifecycle check. Policy-selected staging/mobile coordination uses oldaplib persistent ownership; atomic area teardown checks references/default mappings. 12 focused HTTP tests and 27 StagingArea tests pass; parent combined evidence totals 129 tests plus real isolated library/API integration.
- Open: AS-03 transfer/inventory; native Capture acceptance, reviewed ACL migration, matching library release, persistent-store rollout and recovery rehearsal before activation.
- Risks/Assumptions: Current Redis was not changed. Persistent policy rollout requires all writers upgraded together and a separate durable gate store. No CaptureApp edits, ontology load, memberships or live workflow activation. Generic legacy objectfactory ACL test failure reproduces on original source and remains tracked in parent AS-02 evidence.

### Update 2026-09-07 21:07
- Decisions: Preserve generic update request/response shapes while returning typed permission/value/not-found/reference statuses. Apply existing hierarchy-route restrictions to transitive Shared subclasses.
- Implementation: Rejected non-object and unknown-field writes before persistence, kept absent known-property clears idempotent, returned 400/403/404/409 for typed failures, updated OpenAPI/guide/context, and added six isolated HTTP regression tests (49 combined library/API tests pass).
- Open: AS-02 project policy, preparation-note lifecycle guard, role/ACL union, complete safe domain operations, reference receipts and writer coordination. GraphDB concurrent claims exposed a coordination gap; persistent-gate recovery decision remains pending.
- Risks/Assumptions: Requires accompanying unreleased oldaplib source changes. No CaptureApp formats/source, role grants, ontology load or deployment changed. The accepted post-archive preparation-note rejection is not implemented by this error-mapping increment; no destructive application fixtures were run.

### Update 2026-09-03 19:39
- Decisions: Keep OLDAP's generic in-use protection intact and represent private mobile receipt resource identifiers as non-referential typed URI metadata instead of weakening deletion checks.
- Implementation: Changed new mobile commit and lifecycle receipt resource values to `xsd:anyURI` literals; added a narrow transactional normalizer for the early Step-13D IRI representation after an authorized delete has already encountered an in-use conflict; retried the unchanged deletion guard so real incoming references still block; contradictory legacy metadata now fails closed with a structured `503`; added receipt, normalization, deletion-retry, error-mapping, and real-reference regressions.
- Open: Rebuild/restart matching API and media worker services before repeating the disposable live deletion/re-upload acceptance flow.
- Risks/Assumptions: The normalization preserves immutable receipt values and touches only `urn:oldap:mobile-media-commits`. Existing public routes, payloads, permissions, tokens, IIIF consumers, non-mobile resources, GraphDB application data, and genuine referential-integrity behavior remain unchanged.

### Update 2026-09-02 18:08
- Decisions: Make the authoritative OLDAP staging mutation and its mobile-receipt lifecycle notification one GraphDB transaction. Distinguish moved, staging_deleted, and archived events and expose them only through a separate purpose-authenticated internal worker contract.
- Implementation: Added the durable leased lifecycle outbox and claim/ack routes; connected mobile-origin generic move, delete, and exact archive transformation through oldaplib's additive pre-commit hook while leaving non-mobile mutations unchanged; retained the delivered claim fence so only the exact acknowledgement is replayable; added closed security, lease, rollback, route, and compatibility tests; synchronized OpenAPI and stable context; prepared API 0.2.22.
- Open: Publish oldaplib 0.7.17, update this repository's Poetry lock from 0.7.16, and rebuild oldap-api before enabling Step-13D workers.
- Risks/Assumptions: Outbox delivery is at least once and deliberately fail closed; delayed delivery may retain files and block a re-upload but cannot release early. Existing public routes, payloads, access tokens, media/IIIF consumers, and FasnachtsPage behavior remain compatible.

### Update 2026-08-30 00:13
- Decisions: Align public ZIP job creation with the existing authorizer boundary by accepting only safe QNames in the explicitly selected project, while retaining absolute HTTP(S) and canonical UUID-URN targets.
- Implementation: Passed the validated project short name into target validation, documented canonical response identifiers in OpenAPI, synchronized the media-owned contract copy, and added isolated acceptance/rejection regressions. Six focused import-view tests pass.
- Open: Exercise one real Chama ZIP through SALSAH; immutable report rendering and explicit confirmation remain the next frontend increment.
- Risks/Assumptions: This is an additive request-format extension; responses and existing absolute-IRI clients are unchanged. QName canonicalization remains authoritative in `OldapImportAuthorizer`, and no GraphDB-backed test was run.

### Update 2026-08-29 02:58
- Decisions: Preserve the documented QName-or-absolute-IRI Staging target contract and canonicalize project QNames before custom SPARQL instead of requiring clients to know storage namespaces.
- Implementation: Expanded selected StagingArea/folder QNames through authoritative project metadata, returned canonical absolute target IRIs, documented the response behavior, and added an isolated Chama-shaped regression proving the query never emits `<chama:...>` pseudo-IRIs.
- Open: Restart oldap-api and repeat the single-file Chama Staging upload.
- Risks/Assumptions: Already absolute and URN targets remain unchanged. No GraphDB-backed test was run.

### Update 2026-08-29 01:15
- Decisions: Keep single-file Staging upload authorization in OLDAP and expose only an additive target-resolution endpoint; derive path, quota, default role, and permission server-side and keep Mobile on its dedicated workflow.
- Implementation: Added strict `POST /data/{project}/staging-upload-target`, enriched the shared import authorizer with upload configuration, documented the OpenAPI contract, and added isolated query/HTTP regressions.
- Open: Restart oldap-api before the live SALSAH acceptance upload; aggregate quota usage remains owned by the later unified ingest accounting design.
- Risks/Assumptions: The selected StagingArea must define media path, quota, and an annotated project-local default role. Existing API contracts are unchanged, and no GraphDB-backed tests were run.

### Update 2026-08-28 00:52
- Decisions: Treat every GraphDB-backed API fixture as destructive and fail closed before application setup when it targets the normal local `oldap` repository.
- Implementation: Switched the fixture default to the dedicated `oldap-test` repository, added an explicit `OLDAP_TEST_TS_REPO` resolver/guard with focused non-GraphDB regressions, and documented the test-repository contract.
- Open: Create/provision `oldap-test` before running the legacy integration suite; do not weaken the guard to reuse a development repository.
- Risks/Assumptions: Existing CI or developer setups that implicitly reused `oldap` now fail intentionally until they select a disposable repository. No runtime API behavior changes.

### Update 2026-08-27 17:45
- Decisions: Rebase the two mobile namespace corrections onto the current API 0.2.21 baseline and review only their changed code, tests, and interactions with the newly integrated resource-read fast path.
- Implementation: Preserved both additive namespace fixes while integrating the upstream summary/read changes, resolved the work-log ordering, and reran the focused mobile, StagingArea, and fast-path regression matrix.
- Open: API 0.2.21 still requires the corresponding newer oldaplib release documented by its upstream commits; the checked-in Poetry lock installs 0.7.11, which does not provide `ResourceReadResult`.
- Risks/Assumptions: The 56 mobile/StagingArea tests pass with the locked environment and all 58 relevant tests pass against a temporary read-only export of current oldaplib 0.7.16. The uncommitted patch adds no route, payload, dependency, deployment, or token change.

### Update 2026-08-26 19:35
- Decisions: Resolve mobile-commit Fasnacht vocabulary from the authoritative OLDAP project namespace while preserving every existing account, organisation, role, StagingArea, inbox, and `ADMIN_CREATE` revalidation.
- Implementation: Removed the deprecated hardcoded `http://oldap.org/fasnacht#` prefix from the transactional target query, derived its five project terms from `oldap:namespaceIri`, and updated the focused repository contract test to the live `http://fasnacht.digital/ns/` graph.
- Open: The already compensated local test upload cannot reuse its terminal server generation. The current live test must use a new local media item; an explicit cross-service restart-generation workflow remains a separate recovery decision. No GraphDB migration is required.
- Risks/Assumptions: The project metadata remains authoritative and its namespace ends in the separator required by OLDAP. Existing routes, payloads, token consumers, permission thresholds, and non-mobile operations are unchanged.

### Update 2026-08-26 17:55
- Decisions: Keep the protected `top/Mobile` role policy exact while making valid project-QName input independent of process-local bearer-token context hydration.
- Implementation: Expanded the StagingArea default-role QName through the authoritative project namespace already resolved from GraphDB, added a regression for the current Fasnacht namespace and a fresh bearer context, and documented the boundary.
- Open: Existing StagingAreas without `top/Mobile` must retry the normal FasnachtsPage provisioning flow once this API patch is running; no data migration is required.
- Risks/Assumptions: The patch changes only QName normalization inside the existing create guard. Absolute IRIs, non-project prefixes, the single-role requirement, exact `DATA_VIEW`, and all existing routes remain unchanged.

### Update 2026-08-26 01:01
- Decisions: Add a bounded summary endpoint instead of expanding existing search or single-resource contracts; omit missing and unreadable resources identically, and make media delivery an explicit opt-in enrichment.
- Implementation: Added `POST /data/summaries/{project}` with strict request bounds, selected-property serialization, optional IIIF/external delivery, one oldaplib batch call, OpenAPI 3.1 schemas/examples, a dedicated usage/security guide, and isolated route coverage.
- Open: Publish/install the corresponding oldaplib release before deploying this API revision; run live Chama timing after restart.
- Risks/Assumptions: Batches are capped at 100 IRIs and 32 requested properties. IIIF capabilities are short-lived and clients must not persist them. Existing API routes and payloads are unchanged.

### Update 2026-08-26 00:38
- Decisions: Keep the instance-read HTTP contract unchanged while accepting the complete attached-role map from oldaplib's main resource CONSTRUCT.
- Implementation: Extended the isolated fast-path route regression with two attached roles and exact serialized permissions; synchronized stable context with oldaplib 0.7.13 and the removal of both former follow-up queries.
- Open: Install the next oldaplib release containing integrated role extraction, restart the API, and measure representative resource detail reads.
- Risks/Assumptions: No API implementation change is required beyond the already active structured read result; compatibility depends on publishing/installing the corresponding oldaplib revision.

### Update 2026-08-26 00:24
- Decisions: Consume oldaplib's structured single-CONSTRUCT read result instead of maintaining an API-owned preliminary type query; preserve the existing explicit/inferred type response contract.
- Implementation: Reworked generic instance GET to use `ResourceInstanceFactory.read_data()`, reuse its resolved property model during serialization, and remove duplicate IRI/project validation plus direct QueryProcessor usage; added a GraphDB-independent route regression proving no preliminary connection query.
- Open: Publish/install the corresponding oldaplib release, run the existing GraphDB-backed read-instance test in a disposable fixture repository, restart the API, and measure representative Chama detail reads.
- Risks/Assumptions: The local shared GraphDB fixture suite was not run because it clears administrative/test graphs; focused library and isolated route tests cover the changed contract without mutating the user's repository.

### Update 2026-08-23 19:26
- Decisions: Close the cross-repository Step-11 final-check findings without changing existing public routes or token consumers. Treat the protected Mobile inbox as unavailable to ZIP import, ignore only typed terminal-history references during empty-area deletion, and reuse the common renewable Staging mutation lease for mobile commits.
- Implementation: Added ZIP-import protection at authorization, closed commit validation, and final transactional revalidation; blocked reserved folder names inside ZIP trees; made active ZIP imports block StagingArea deletion while typed terminal import records and permanent mobile receipts no longer make empty areas undeletable; delegated mobile commit serialization to the heartbeat-renewed shared lock; aligned internal comment validation, German RDF language, and the OpenAPI description; and added blank local environment placeholders plus focused regression coverage.
- Open: Production enablement still requires operator-provisioned matching internal credentials and an explicit deployment. Existing GraphDB-backed legacy suites remain subject to their documented destructive fixture constraints.
- Risks/Assumptions: Historical-reference exemptions apply only to typed records in the two application-owned history graphs. Unknown external references still block deletion, and malformed referenced import payloads fail closed.

### Update 2026-08-22 16:48
- Decisions: Complete a two-pass merge-readiness review of the full uncommitted Step-11B and Redis-isolation scope before push. Keep generic non-Staging routes independent of the new policy, protect the complete `top`/`Mobile`/`Trash` system structure, and fail closed when a Staging resource changes class while a request waits for the shared lease.
- Implementation: Moved fresh Staging instance reads and payload application inside the Redis lease, added class-drift rejection for update/delete/transform, avoided constructing Staging policy for ordinary creates, protected direct `Trash` mutations, rejected malformed or misplaced legacy reserved-folder aliases, documented the required Redis `noeviction` policy, updated OpenAPI, and added focused compatibility, structure, and concurrency regressions.
- Open: Step 11C remains in oldap-mediaserver. Deployment must retain cache DB 0, lock DB 1, and Redis `noeviction`. The local GraphDB test repository may need user-controlled restoration: an accidentally included legacy fixture cleared `oldap:admin` and `hyha:*` before failing on its stale `OLDAPBASE`; no automatic reconstruction was attempted.
- Risks/Assumptions: The isolated final matrix passes 134 backend tests, OpenAPI validation, Python compilation, Black for the new formatted modules/tests, Poetry metadata validation with existing deprecation warnings, and whitespace checks. Six additional legacy tests were not available because their destructive global fixture expects `/Users/rosman00/PycharmProjects/oldaplib`; they were not rerun with a corrected path to avoid further GraphDB mutation. Logical Redis databases still share one server, memory budget, and administrative failure domain.

### Update 2026-08-22 16:22
- Decisions: Keep one API-owned Redis server while isolating oldaplib cache clearing from the Step-11A/11B Staging lease through separate logical databases. Fail before production startup when the dedicated lock URL is absent or resolves to the cache database.
- Implementation: Added credential-free Redis database identity validation, moved both Staging lock clients to `OLDAP_STAGING_LOCK_REDIS_URL`, configured cache DB 0 and lock DB 1 for Docker and local workflows, documented the operational contract, and added focused overlap, default-DB, credential, transport, client-wiring, and pre-`FLUSHDB` startup regressions.
- Open: Deployment operators must retain the documented DB 0/DB 1 environment values. Step 11C must not connect oldap-mediaserver to this API-owned Redis.
- Risks/Assumptions: The non-destructive final matrix passes 110 focused Redis, Staging, mobile-commit, ZIP-import, transaction, security, and compatibility tests plus Black, Python compilation, Poetry metadata, and whitespace checks. Logical databases share one Redis process and memory budget, but `FLUSHDB` is database-scoped; Redis `FLUSHALL` or external administrative deletion remains an operator-controlled outage. No Redis domain data, second container, oldaplib change, API route, payload, or token behaviour was introduced. A real app start was deliberately omitted because existing startup behaviour clears cache DB 0.

### Update 2026-08-21 22:04
- Decisions: Finalize Step 11B only after a two-pass merge-readiness review of the complete uncommitted oldap-api and FasnachtsPage scope. Keep the user's partially restored local GraphDB data untouched and prefer non-destructive contract/unit verification for this pass.
- Implementation: Made project graph resolution reliable for fresh bearer-only workers, brought the registered legacy `/admin` resource-create route under the shared Staging policy, matched `ADMIN_OLDAP` deletion authority to `oldap:SystemProject`, moved update policy checks inside the global write lease, mapped malformed area IRIs to HTTP 400, and made the atomic empty-area endpoint the exclusive generic delete/transform boundary for StagingAreas. Added focused regressions for every correction, expressed the fixed `master.tif` publication evidence in generator-compatible OpenAPI, and synchronized the downstream typed client.
- Open: Step 11C belongs to oldap-mediaserver; this repository is next required for the Step-11D media-to-OLDAP commit call. The separately documented default-role/Mobile-role migration decision remains open.
- Risks/Assumptions: The final non-destructive matrix passes 102 focused oldap-api tests, OpenAPI validation, Python compilation, Black for every newly formatted module, Poetry metadata validation with existing deprecation warnings, whitespace checks, 124 FasnachtsPage tests, focused frontend ESLint, and the production build. The full GraphDB-backed oldap-api suite was deliberately not rerun because its fixtures would alter the user's partially restored local dataset; the prior complete-run result remains recorded below.

### Update 2026-08-21 19:26
- Decisions: Complete Fasnacht Capture Step 11B additively: keep GraphDB as the durable authority, serialize every Staging mutation that can race with mobile commits or teardown through one renewable bounded Redis lease, and expose a dedicated atomic empty-StagingArea deletion instead of weakening generic CRUD. Preserve every existing route and token consumer.
- Implementation: Added fail-closed `top`/`Mobile` identity, placement, casing, child, role-policy, transform, move, rename, and delete guards across generic and ZIP-import writes; added current-permission/reference revalidation and one-transaction deletion of `Mobile`, `Trash`, `top`, and the StagingArea; documented the additive OpenAPI route; and covered transaction rollback, ambiguity, authorization, lock renewal/failure, generic compatibility, and request replay. The final compatibility review also retained transform adapters that provide `expectedSourceClass` without a concrete instance `name`.
- Open: Step 11C belongs to oldap-mediaserver; this repository is next required for the Step-11D media-to-OLDAP commit call. The existing FasnachtsPage default-role editor does not atomically migrate the protected Mobile role policy; changing that role can therefore make mobile commit validation fail closed and needs a separately reviewed coordinated contract if such changes must remain supported.
- Risks/Assumptions: Redis coordinates read-committed GraphDB writers but stores no authoritative result. The focused final matrix passes 103 tests; the complete repository run passes 863 tests, with only the three previously documented unrelated failures in extended-user datamodel parsing and the expanded `rdfs:Resource` inference expectation. No oldaplib, ontology, deployment, secret, existing route, or token behavior changed.

### Update 2026-08-21 16:38
- Decisions: Tighten the new Step-11A boundary before merge without changing existing routes: bind trusted publication evidence to durable byte length and exact storage path, and preserve the established RDF datatypes used by normal staging uploads.
- Implementation: The final two-pass review blocked global event reuse, detected incomplete duplicate roots, enforced exact publication-path agreement, restored `xsd:anyURI`/`rdf:langString` output, rejected noncanonical paths, invalid Unicode, malformed IRI syntax, and JSON type confusion, and revalidated all permanent-receipt index facts. The OpenAPI contract and 60 focused transaction/idempotency/security/compatibility tests now cover the boundary; real Redis serialization and all four generated GraphDB read queries were also exercised locally.
- Open: Step 11B must protect the system inbox and add atomic empty-StagingArea deletion. Steps 11D/11E must send media-confirmed `byteLength` and `storagePath`, provide operator-managed credentials, expose only the intended internal route, and run physical cross-service acceptance. The final complete repository run passes 838 tests; three unrelated existing failures remain in extended-user datamodel parsing and the expanded `rdfs:Resource` inference expectation.
- Risks/Assumptions: GraphDB remains read-committed, so the bounded Redis lease is required whenever this endpoint is enabled; the permanent GraphDB receipt remains authoritative after a lost lease or response. No oldaplib, ontology, deployment, secret, or existing consumer behaviour was changed.

### Update 2026-08-20 19:15
- Decisions: Add the mobile commit as an internal, additive, purpose-authenticated operation without changing existing routes or token consumers. Keep GraphDB as the permanent receipt authority and serialize its read-committed check-and-insert across Gunicorn workers with a bounded Redis lease.
- Implementation: Added the closed `/internal/mobile-media/v1/uploads/{uploadId}/commit` contract, strict service JWT isolation, live account/organisation/role/StagingArea/ADMIN_CREATE and protected `top/Mobile` revalidation, server-derived staging triples, atomic resource-plus-receipt persistence, exact replay/conflict handling, strict GraphDB result and media-origin validation, stable privacy-preserving errors, OpenAPI documentation, and 44 focused transaction/idempotency/security/compatibility tests. Declared the already resolved Redis 7.4 runtime dependency explicitly.
- Open: Step 11B must protect the system inbox and add atomic empty-StagingArea deletion. Steps 11D/11E must implement the media caller, provide operator-managed service credentials, expose only the intended internal route, and run real cross-service acceptance. Across the complete legacy run and the corrected-dependency rerun, 816 tests pass; three unrelated existing failures remain in extended-user datamodel parsing and the now-expanded `rdfs:Resource` inference expectation.
- Risks/Assumptions: GraphDB exposes read-committed rather than serializable transactions; the Redis lease therefore remains required whenever this endpoint is enabled. Redis stores no commit result, and a lost lease returns retryable `503` so the caller resolves the permanent GraphDB receipt. No oldaplib, ontology, deployment, secret, or existing consumer behaviour was changed.

### Update 2026-08-19 22:33
- Decisions: Treat validated HEIC and HEIF originals as the same closed still-image delivery family as JPEG, TIFF, and PNG.
- Implementation: Extended the import commit validator and OpenAPI enum with `image/heic` and `image/heif`, regenerated the FasnachtsPage Zod contract, and added commit regression coverage.
- Open: Deploy in lockstep with the HEIF-capable mediahelper image and run one test-system ZIP import through commit.
- Risks/Assumptions: The API trusts only the media-owned manifest facts; actual HEIF decoding remains outside the API process.

### Update 2026-08-16 23:44
- Decisions: Separate environment-selected export policy from the immutable 50 GB v1 safety ceiling; freeze the selected size limit in each manifest and retain reservations until physical cleanup is proven.
- Implementation: Added strict archive/READY/audit and per-user/system active-job/retained-byte configuration, atomic GraphDB quota checks, dynamic estimate/manifest limits, stable HTTP 429 quota errors, and removed the unsafe production download-origin fallback. OpenAPI and concurrency/retention/limit coverage are synchronized; all 118 focused export tests pass.
- Open: Measure a representative large production inventory and complete deployed SMTP plus Windows/macOS and spreadsheet acceptance.
- Risks/Assumptions: Default quotas are 3/20 active jobs and 100/500 GB retained source bytes (user/system); operators may lower them within validated bounds. Source bytes are deliberately conservative until `DELETED`.

### Update 2026-08-16 00:07
- Decisions: Close Archive export Phase 2 after the user-approved source-data correction and a complete live ARCHIVE_ALL lifecycle; retain production credentials/SMTP and capacity measurements as Phase-3 work.
- Implementation: The normal authenticated ArchiveUnit CRUD path changed `fasnacht:bmg-undatiert` to the portable label `Undatierte Dokumente und Medien`. A live ARCHIVE_ALL request then reached READY with 20 unit directories, one original, zero warnings, exact CSV hierarchy evidence, matching archive SHA-256, protected GET/HEAD/Range delivery, and DELETED cleanup with no remaining artifact or usable capability.
- Open: Production credentials/SMTP and representative capacity/performance measurements.
- Risks/Assumptions: The persistent label edit was explicitly authorized. The current live inventory contains no external or unreadable warning example; focused projector/reauthorization tests cover those cases.

### Update 2026-08-15 23:58
- Decisions: Accept canonical OLDAP QNames at the generic export request boundary because generic search returns them, while retaining strict absolute HTTP(S)/UUID URN support and rejecting traversal-like values. Validate archive names only when they participate in the selected export path; never let an unrelated invalid root block a selected subtree.
- Implementation: Added QName request validation and OpenAPI descriptions, contextual unsafe ArchiveUnit errors, lexical extraction for OLDAP language-aware scalar values, and regression coverage for unrelated invalid roots and language suffixes. Accepted live `fasnacht:bmg-stamm-1908` through GraphDB, the HTTP job/claim lifecycle, worker recovery, capability issuance, exact ZIP/checksum inspection, and DELETED cleanup. All 98 export tests and changed-file Black checks pass.
- Open: Deliberately correct the live ArchiveUnit name `Undatierte Dokumente/Medien`, then rerun successful ARCHIVE_ALL. Production credentials/SMTP and representative capacity measurements remain deployment/hardening work.
- Risks/Assumptions: QName validation proves syntax, while project context and requester permissions remain authoritative in the OLDAP reader. The whole-archive rejection is intentional portable-path safety, not a transport failure.

### Update 2026-08-15 23:24
- Decisions: Extend the existing cross-system physical acceptance rather than creating a second Archive-only harness; keep the worker project- and ontology-neutral by driving it exclusively from the closed Archive manifest.
- Implementation: Added an `ARCHIVE_UNIT` acceptance case that passes a real API job/manifest through claim, manifest delivery, `SequentialExportWorker`, and `ExportArtifactStore`, then verifies READY state, the original bitstream, standard support files, BOM/RFC-4180 `archive-units.csv`, common unit fields, and profile metadata. All 96 export tests and Black check pass.
- Open: Run authenticated browser and HTTP acceptance against a representative live ArchiveUnit/whole archive, including external/unreadable warnings, capability download, and deletion.
- Risks/Assumptions: The deterministic acceptance uses in-memory API persistence and a temporary filesystem while exercising the production lifecycle/worker implementations; GraphDB, HTTP, projection, and reauthorization remain covered by their focused tests.

### Update 2026-08-15 23:18
- Decisions: Enable Archive kinds only through the same requester identity used for snapshot reads and only after adding profile-, hierarchy-, resource-, and relationship-aware download reauthorization. Treat a linked but unreadable medium as an opaque warning, never as guessed source metadata.
- Implementation: Added `OldapArchiveInventoryReader`, permission-bound profile label resolution, unavailable-link projection, Archive download authorization, and closed Staging/Archive projector/authorizer routers. Removed the Archive-kind runtime rejection and wired ARCHIVE_UNIT/ARCHIVE_ALL into the public estimate/create services. Updated runtime documentation and HTTP contracts; all 95 export tests, Black, and OpenAPI validation pass.
- Open: Implement ArchiveTree unit/all export actions, then execute a physical Archive ZIP acceptance including `archive-units.csv`, external/unreadable warnings, download, expiry, and manual deletion.
- Risks/Assumptions: Missing labels remain empty while stable IRIs are retained. Bounded class searches plus per-IRI label reads favor authorization correctness; latency must be measured against representative holdings before production capacity tuning.

### Update 2026-08-15 23:02
- Decisions: Put archive hierarchy, shared archival description, and project-profile values in the immutable API snapshot; keep the media worker ontology-blind. Add `archiveUnits` only to Archive manifests so accepted Staging canonical payloads remain unchanged.
- Implementation: Added `ArchiveSnapshotProjector` with closed records/protocols, ARCHIVE_UNIT/ARCHIVE_ALL hierarchy paths, empty-unit retention, multi-unit media deduplication and relationship metadata, external exclusions, size/source checks, and cycle/portable-collision rejection. Extracted shared safe snapshot path/source primitives, then extended runtime and JSON Schema validation to bind archive units, directories, parent references, and media containers. All 90 focused export tests pass and Draft 2020-12 schema validation succeeds.
- Open: Implement `OldapArchiveInventoryReader`, label resolution and Archive download reauthorization; compose the runtime projector/authorizer and enable the public Archive kinds.
- Risks/Assumptions: The projector currently consumes an already requester-authorized inventory; unreadable-subtree behavior therefore remains unproven until the concrete OLDAP reader is integrated. Shared binary/path primitives now have one documented `snapshot_common.py` source instead of cross-module private reuse.

### Update 2026-08-15 22:26
- Decisions: Treat wall-clock time as input to expiry tests and close export Phase 1 on an isolated physical cross-system acceptance; production credentials, provider SMTP, and 50 GB capacity remain separate deployment/hardening gates.
- Implementation: Added a bridge acceptance suite using the real API worker service, media `SequentialExportWorker`, and artifact store for small, 32 MiB, changed-source failure, console notification, expiry, manual cleanup, ZIP content/digest, and physical deletion. Hardened the JWT expiry assertion against calendar drift while retaining the exact claim check. All 86 export tests pass and the three changed test modules pass Black.
- Open: Provision production purpose-specific credentials and SMTP/public URL settings, measure representative holdings, and implement the Archive projector in Phase 2.
- Risks/Assumptions: The acceptance suite isolates persistence in memory while exercising the real lifecycle and media filesystem implementations; GraphDB repository/HTTP boundaries retain their dedicated tests. Console mail verifies composition and transport invocation, not an external SMTP provider.

### Update 2026-08-15 00:20
- Decisions: Reuse the proven import notification policy without coupling import/export types. Persist READY/FAILED outbox state in the same lifecycle write, keep mail evidence version-neutral, expire READY before cleanup claims, and remove only already content-free audit hulls after 60 days.
- Implementation: Added the closed export notification state, token-free German status messages, console/SMTP delivery, three-attempt five-minute retry/reconciliation, stale READY-mail suppression after deletion, explicit READY -> EXPIRED -> DELETING progression, audit pruning, GraphDB/in-memory persistence operations, OpenAPI exposure, environment documentation, and regenerated frontend types. All 88 focused export/authentication tests and OpenAPI validation pass; the FasnachtsPage production build succeeds.
- Open: Provision export service/download credentials and SMTP/public-app settings, activate the media worker, run deployed expiry/mail/download smoke tests, then implement Archive projection and the Staging UI.
- Risks/Assumptions: SMTP submission is bounded at-least-once; if the provider accepts a message but persistence of SENT fails, a retry can duplicate it. No secret value or live job was changed.

### Update 2026-08-15 00:02
- Decisions: Bind the immutable manifest to the requester IRI as well as the existing job/scope/profile/inventory identity so the project-neutral worker can produce an auditable `export.csv` without a user token or a second API lookup.
- Implementation: Added required `requestedByIri` to the runtime manifest, JSON Schema, Staging projection, service calls, job identity validation, and fixtures. The paired media worker consumes the field as opaque export metadata; all 78 focused export/authentication tests pass.
- Open: Add READY/FAILED outbox and expiry reconciliation, Archive projection, and deployed purpose-specific secrets.
- Risks/Assumptions: Requester IRI is intentionally included in the downloadable support CSV; it is already known to the export owner and never used by the worker for authorization.

### Update 2026-08-14 23:31
- Decisions: Make worker leases and result identity durable in the export job; prioritize cleanup before builds, invalidate active BUILD claims on user cancellation, and require an unexpired exact claim for every manifest/result operation. Treat cleanup proof as the atomic boundary that deletes the frozen manifest and redacts selection path/IRI from the retained audit record.
- Implementation: Added atomic BUILD/CLEANUP claim and reclaim, fixed-duration heartbeat renewal, active-claim manifest reads, digest-bound idempotent READY/FAILED and cleanup results, 24-hour READY/60-day audit timestamps, GraphDB active-claim indexing and manifest purge, dedicated export-service JWT authentication, non-token-issuing service credentials, and all five internal Flask routes. Added failure, replay, cancellation, stale-worker, HTTP-auth, and GraphDB transaction coverage; all 78 focused export/authentication tests pass.
- Open: Implement the media-local ZIP builder, private partial/final artifact storage, download/cleanup routes, READY/FAILED notification outbox, Archive projection, expiry reconciliation, and deployed credentials/secrets.
- Risks/Assumptions: GraphDB transaction isolation remains the concurrency authority for queue claims. No deployed secret or service credential was populated, and no live GraphDB or media artifact was mutated.

### Update 2026-08-14 23:12
- Decisions: Expose only the fully authorized Staging export scopes; fail Archive kinds explicitly until their projector exists. Keep runtime profiles server-owned and project-neutral, and reauthorize every frozen included Staging source before issuing a READY download capability.
- Implementation: Added the validated file profile registry with bundled `fasnacht-v1`, public estimate/create/list/read/delete/download-capability services and Flask routes, atomic job-plus-manifest creation, owner/cursor/version enforcement, current-visibility download authorization, OpenAPI response alignment, package data, environment documentation, and regenerated frontend schemas. All 67 focused export/authentication tests, Python compilation/format checks, OpenAPI validation, and the FasnachtsPage production build pass.
- Open: Implement internal worker claim/manifest/result/cleanup routes, the media-local builder and private artifact lifecycle, READY/FAILED outbox transitions, Archive projection, and deployed secret configuration.
- Risks/Assumptions: The public routes require distinct export service/download secrets in each deployed environment; no secret value was created or changed. Generated `zod.ts` retains its existing generator-wide ESLint baseline, while the production build succeeds.

### Update 2026-08-14 22:47
- Decisions: Keep the export source credential isolated from the import-record key as well as every other API/media trust domain.
- Implementation: Documented the required `OLDAP_EXPORT_SERVICE_JWT_SECRET` in the local environment example, extended API-side key separation, and made SHA-256 mandatory in resolver responses. The paired media route is implemented; all 50 focused API export tests and 17 focused media checks pass.
- Open: Add the export-service secret to the deployed oldap-api environment and activate the public export endpoints.
- Risks/Assumptions: The media resolver performs synchronous streaming digests; production-scale request timing remains to be measured.

### Update 2026-08-14 22:31
- Decisions: Project Staging exports exclusively through the requester's permission-filtered OLDAP connection; never trust browser sizes or RDF paths as filesystem authority. Resolve local originals in batches of at most 1,000 through a dedicated one-minute `export-source-resolver` service JWT. Exclude Trash and descendants and preserve external records as explicit non-file manifest rows.
- Implementation: Added `OldapStagingInventoryReader`, project-neutral folder/media DTOs, `StagingSnapshotProjector` for `STAGING_FOLDER`/`STAGING_ALL`, profile metadata projection, safe NFC/portable path construction, cycle/collision/inventory/size validation, estimate output, and immutable manifest generation. Added `MediaBinarySourceResolver` with strict response reconciliation and key separation. Added 13 tests; all 49 focused export tests pass. The paired media OpenAPI contract is validated.
- Open: Implement the MediaServer resolver route and wire public estimate/create/read/list plus internal manifest endpoints; then add permission-aware IRI label resolution, Archive projection, worker claims/results, and READY/FAILED outbox events.
- Risks/Assumptions: RDF has no original byte-size fact, so runtime snapshot creation depends on the not-yet-implemented internal media resolver. Staging profile projections with `resolveLabels` fail closed until a permission-aware shared label resolver exists. No public route or live GraphDB/filesystem mutation was added.

### Update 2026-08-14 16:21
- Decisions: Publish each export job and its separate immutable worker manifest in one GraphDB transaction. Use RFC 8785 and SHA-256 for cross-service identity, require expected original sizes for all included media, and bind manifest scope/profile/selection/inventory/time exactly to the job. Add notification outbox records later with the concrete READY/FAILED transition rather than as unused scaffolding.
- Implementation: Added `ExportManifest` canonicalization, closed-envelope and inventory validation, job binding, atomic `create_with_manifest`, immutable digest-verified manifest reads, and the `rfc8785` runtime dependency. Updated the v1 JSON Schema and added canonicalization, mismatch, corruption, duplicate, atomicity, and negative tests; all 36 focused export tests pass.
- Open: Implement the authorized profile-backed GraphDB snapshot projector and wire estimate/create/read/list plus internal manifest routes; add outbox events with worker-result transitions.
- Risks/Assumptions: Manifests are separate resources in the export named graph, avoiding job-payload inflation but still sharing its transaction. A manifest byte ceiling awaits representative dataset measurements. No live GraphDB or filesystem state was mutated.

### Update 2026-08-14 14:19
- Decisions: Persist export jobs as canonical internal JSON plus minimal owner/state/version/time indexes in the dedicated `urn:oldap:export-jobs` graph. Keep potentially large immutable manifests outside the job literal and require atomic existence/version checks for every write.
- Implementation: Added full `ExportJob`, selection, progress, and timezone-aware timestamp deserialization. Added `GraphDbExportJobRepository` create/get/list/save operations with transactional duplicate prevention, exact +1 optimistic locking, owner/state SPARQL filtering, and canonical payload writes. Added six focused persistence tests; all 29 export domain/repository tests pass.
- Open: Implement the profile-backed authorized GraphDB snapshot projector, register public/internal Flask routes, and add READY/FAILED outbox events.
- Risks/Assumptions: The durable repository is not yet wired to HTTP because job and manifest publication must become one atomic application operation. No live GraphDB or filesystem state was mutated.

### Update 2026-08-14 12:36
- Decisions: Start ZIP-export Phase 0 contract-first with a project-neutral security/lifecycle core and strictly declarative, versioned project metadata profiles. Fix the approved 50 GB, 24-hour, `DATA_VIEW`, and 60-day values in the shared domain rather than in FasnachtsPage.
- Implementation: Added immutable optimistic export jobs, strict build/cleanup claim invariants, a repository protocol with an in-memory reference implementation, purpose-specific short-lived download capabilities, and a `ProjectExportProfile` parser that rejects binary/security overrides and executable behavior. Added canonical profile/manifest/CSV fixtures and 23 focused tests. Defined public estimate/job/capability and internal worker claim/manifest/result/cleanup operations in the validated main OpenAPI; FasnachtsPage regenerated its typed client from this contract.
- Open: Implement manifest/outbox persistence, profile-backed GraphDB snapshot projection, Flask routes, and media-worker integration; then measure representative datasets.
- Risks/Assumptions: OpenAPI defines the frozen Phase-0 interface, but this slice exposes no runtime HTTP endpoint and performs no GraphDB or filesystem mutation. The Python profile boundary remains authoritative for cross-field and reserved-property rules.

### Update 2026-08-13 23:58
- Decisions: Expose Staging subtree movement through a dedicated endpoint and prevent hierarchy changes through generic instance update, mirroring the existing ArchiveUnit integrity boundary.
- Implementation: Added `POST /data/{project}/{instiri}/staging-folder-move`, OpenAPI request/response schemas, stable 400/403/404/409/503 mappings, and four HTTP contract tests.
- Open: Release/install the corresponding oldaplib version before deploying this API revision.
- Risks/Assumptions: The endpoint deliberately cannot move a folder to the tree root; user folders must remain below a valid parent. Eight focused Staging/archive move contract tests pass against the local GraphDB, and the OpenAPI YAML plus Python modules validate.

### Update 2026-08-12 00:04
- Decisions: Keep generic instance GET responses bounded by the concrete OLDAP resource model rather than exposing or failing on GraphDB-inferred external predicates.
- Implementation: Pass the generated instance class's resolved direct/inherited property map into `ResourceInstance.read_data()`; oldaplib now filters both unknown-IRI and known-QName predicates outside that model.
- Open: Consume the forthcoming oldaplib patch release, restart the API, and retry the affected Fasnacht ArchiveMediaObject GET.
- Risks/Assumptions: All nine GraphDB-backed instance-read tests pass with the local oldaplib checkout; production still requires a published dependency update.

### Update 2026-08-11 00:18
- Decisions: Reconcile all version sources to the last valid tag `v0.2.16` before creating the intended 0.2.17 release; retain the functional oldaplib `^0.7.9` dependency change. Require a non-mutating validation pass before every Makefile-managed version bump.
- Implementation: Restored `tool.poetry.version`, `tool.bumpversion.current_version`, and `oldap_api.__version__` to 0.2.16 after partial bump attempts; added dry-run guards to patch/minor/major Make targets; verified that the next patch bump would consistently update both files, create the bump commit, and tag `v0.2.17`.
- Open: Commit this corrective baseline, then run `make bump-patch-level`; that command will create/tag 0.2.17 and push it after the dry-run succeeds.
- Risks/Assumptions: Existing pushed commits contain inconsistent intermediate 0.2.17/0.2.18 metadata but no corresponding tags. A forward corrective commit preserves history and avoids destructive rewriting of `main`.

### Update 2026-08-11 00:04
- Decisions: Require published oldaplib 0.7.9 for the production fix and prepare oldap-api 0.2.17; do not rely on the local editable checkout used during diagnosis.
- Implementation: Raised the API dependency floor from `^0.7.0` to `^0.7.9`, updated package/runtime versions to 0.2.17, resolved the local environment to the published 0.7.9 wheel, verified the exact `Xsd_string` to `Xsd_anyURI` regression through site-packages, passed all seven instance-update tests and Python compilation, and built the 0.2.17 sdist/wheel.
- Open: Build and publish the oldap-api 0.2.17 container, update the deployment tag, deploy, and repeat the production Staging move.
- Risks/Assumptions: `poetry.lock` is intentionally ignored in this repository, so the Docker build resolves from the explicit `^0.7.9` constraint. No production service or image was changed by this preparation.

### Update 2026-08-10 23:01
- Decisions: Keep credentialed CORS environment-specific and exact-origin based. Local development accepts HTTPS and optional HTTP Vite origins on ports 5173/5174; home and production retain their separate deployed-origin allowlists.
- Implementation: Added `https://localhost:5173` and `https://localhost:5174` to the local API environment, synchronized the README example and secure-cookie guidance, restarted the development API, and verified credentialed POST preflights for both HTTPS origins.
- Open: Retry the Staging media drop in the already authenticated FasnachtsPage browser session.
- Risks/Assumptions: The local `.env.local` remains untracked secret-bearing runtime configuration. Home already allows `https://fasnacht.home.org`; production already allows `https://fasnacht.digital`. No broad wildcard CORS policy was introduced.

### Update 2026-08-10 21:57
- Decisions: Expose archive YAML through authenticated request identities only; keep Staging export read-only and import create-only, two-step, exact-hash-bound, and independent of media transformation.
- Implementation: Added proposal download plus preflight/apply blueprints, central oldaplib service integration, 2 MB/5,000-unit limits, safe attachment headers, current-state/permission rechecks, structured plans/results/errors, success/failure audit logging, OpenAPI and operations documentation, and nine focused service/HTTP tests.
- Open: Install the future oldaplib release, run GraphDB-backed authenticated export/preflight/apply, and regenerate downstream clients if they adopt the JSON endpoints directly.
- Risks/Assumptions: GraphDB-backed archive-tree tests could not run because localhost:7200 is unavailable; route contract tests are isolated and pass. Best-effort rollback failures surface as HTTP 500 details for the authorized caller.

### Update 2026-08-09 23:35
- Decisions: Separate the browser-facing media ingest/delivery origin from the optional API-to-media retained-record route; preserve the public URL as a backward-compatible fallback and keep production on verified HTTPS.
- Implementation: `ImportRecordClient` now prefers `OLDAP_MEDIA_INTERNAL_URL`; added home/internal and production/fallback regression tests, local configuration examples, synchronized runtime/project documentation, and prepared patch release 0.2.15.
- Open: Deploy a new API image and the matching `oldap-setup` environment contract, then refresh the retained READY report on `api.home.org`.
- Risks/Assumptions: The home-only internal route uses HTTP between the two trusted test VMs because Caddy's private CA is not installed in the API container. Browser uploads and public media URLs remain HTTPS; production uses HTTPS for both routes.

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
