# OLDAP API Codex Context

OLDAP API is a Flask REST API that exposes OLDAP administration, data modelling,
hierarchical list, resource, and instance operations backed by GraphDB through
`oldaplib`.

## Repository State

- Authentication uses 15-minute access JWTs plus absolute-lifetime refresh JWTs. Existing browser routes retain the secure HttpOnly refresh-cookie contract. Additive `/mobile/v1/auth/login` and `/mobile/v1/auth/refresh` routes expose the same Variant D tokens in JSON for native Keychain/Keystore storage without setting or reading authentication cookies. Refresh reloads current user permissions and checks `authVersion`; `/admin/auth/logout` performs global refresh revocation.
- All protected user, project, role, resource, hierarchical-list, datamodel, and instance routes authenticate through `oldap_api.authentication.require_auth`. The boundary strictly parses Bearer credentials, creates the request-scoped `Connection`, and emits one cache-safe `401` response for missing, malformed, expired, wrong-purpose, or invalid access tokens.
- Python project managed by Poetry.
- Main package: `oldap_api`.
- OpenAPI contract: `API-def/oldap-api.yaml`.
- Instance search documentation: `doc/search_instance.md`.
- Tests live in `oldap_api/test` and rely on a local GraphDB repository plus
  OLDAP test data from the sibling `oldaplib` repository.
- The API requires `oldaplib` 0.7.x and currently locks 0.7.2, which includes
  the shared Variant D and media capability-token support.
- ZIP import Phase 2 is complete. The API owns an immutable-target
  `ImportJob` domain, GraphDB persistence with optimistic state versions and
  atomic staging-area quota sums, purpose-specific upload capabilities, and
  public create/list/read/reissue/cancel/confirm routes, a purpose-specific
  internal service JWT boundary, idempotent SIP-stored handoff, global
  single-worker claim leases, heartbeats, and idempotent READY/INVALID/FAILED
  validation results with quota reconciliation, checksum-verified protected
  report proxying, separately persisted bounded import-email submission,
  opaque cursor pagination, and privacy-preserving operational audit events.
  Media-owned direct SIP ingress and quarantine begin in Phase 3;
  import/cleanup completion events belong to the later execution phases.
  VALIDATE claims also carry immutable job creation time, requester IRI,
  original filename, and actual compressed byte count so media can build its
  validation manifest without a user-authorized lookup. A claim-bound target
  preflight accepts only the ZIP's explicit/implicit root names and types,
  reads current direct staging children with the dedicated GraphDB service
  connection, and returns bounded target-change/folder-collision/media-warning
  findings using the ZIP validator's NFC/portable key semantics.
- ZIP import Phase 5 is complete. `POST /internal/imports/{id}/commit`
  accepts only the active IMPORT claim and a closed, manifest-bound complete
  folder/media mapping. It derives deterministic UUIDv5 staging IRIs, rechecks
  the original user's live ADMIN_CREATE and DATA_UPDATE rights, target identity,
  default role, direct-child names, resource IRIs, and asset IDs inside the same
  GraphDB transaction that inserts the complete hierarchy and changes the job
  to IMPORTED. Imported media persist the same public `shared:serverUrl`
  delivery fact as normal media-server uploads, derived from
  `OLDAP_MEDIA_INGEST_URL` with the IIIF Image API 3 path for images. Exact
  resource audit dates are emitted as `xsd:dateTimeStamp`, matching inherited
  `oldap:Thing` properties and oldaplib's read/update expectations. Exact
  event replay returns the retained relative-path/resource
  mapping; no resource write can survive a rejected job update.
  A companion `POST /internal/imports/{id}/failed` accepts only an active IMPORT
  claim plus proof that promoted assets were compensated and temporary payload
  deleted, then atomically records terminal FAILED and releases its reservation.
  Exact failure-event replay is retained for media/API outage recovery.
  FasnachtsPage now submits READY confirmation with the reviewed state version
  and follows IMPORTING to IMPORTED or compensated FAILED. Phase 6 has started:
  the API atomically selects stale UPLOADING, expired READY, and cleanupPending
  terminal jobs for CLEANUP while explicitly excluding IMPORTING. Only an
  idempotent deletion-proof result finalizes EXPIRED or clears cleanupPending;
  IMPORTED keeps its extracted-byte quota. Durable callback receipts, expired
  task leases, deterministic asset/commit replay, and idempotent cleanup cover
  the remaining ingest recovery states without heuristic orphan deletion.
  Failed/PENDING import email is retried by the API only on idle worker polls,
  at most three times and at five-minute spacing; SMTP never crosses into media.
  The automated Phase 6 lifecycle matrix now covers the complete happy path,
  concurrent quota/claim/confirmation races, and cross-service recovery
  boundaries. Physical disk admission is enforced by media; operations
  operations runbook is maintained in oldap-mediaserver under
  `docs/zip-import/v1/OPERATIONS_RUNBOOK.md`; safe paired 30-/90-day record
  pruning, feature activation, and deployed pilots remain.
- Retained ZIP-import reports use the optional server-to-server
  `OLDAP_MEDIA_INTERNAL_URL`, falling back to the public
  `OLDAP_MEDIA_INGEST_URL`. Browser upload capabilities and persisted public
  media delivery URLs always remain on `OLDAP_MEDIA_INGEST_URL`; this permits
  the home deployment to use internal HTTP without weakening production HTTPS.

## Architecture

- `oldap_api.factory.factory()` creates the Flask app and registers all
  blueprints from `oldap_api/views`.
- View modules translate HTTP payloads and query parameters into `oldaplib`
  calls, then serialize OLDAP/XSD values into JSON.
- Instance create/update payloads are documented in `API-def/oldap-api.yaml`
  as ontology-driven maps; `oldap:attachedToRole` is the special instance
  permission map and supports role-to-DataPermission replacement plus `add`/`del`
  patches on update.
- Structured instance search accepts direct property filters, hierarchical-list
  filters, Lucene field filters, and one-hop linked-resource filters in the
  `filter` array. Linked filters require an `oldaplib` version exposing
  `LinkedResourceSearchFilter`.
- `POST /data/{project}/{instiri}/transform` is the generic resource lifecycle
  endpoint for atomic class transformations that keep the same IRI. It delegates
  the ontology validation and GraphDB transaction to `oldaplib`. Its optional
  `linkFrom` object can add one validated source-resource object-property link
  in the same transaction; the source requires a fresh `DATA_UPDATE` check and
  any link failure rolls back the class transformation.
- `POST /data/{project}/{instiri}/archive-move` is the narrow mutation boundary
  for `shared:ArchiveUnit` hierarchy changes. It delegates cycle detection plus
  the parent/optional-position update to `oldaplib.ArchiveTree`; the generic
  instance-update route rejects these structure fields on archive units so HTTP
  clients cannot bypass the check. Deployment requires an `oldaplib` release
  that exposes `oldaplib.src.archive_tree`.
- `oldaplib` owns GraphDB access, domain validation, resource instance classes,
  permissions, and data model interpretation.
- The API should avoid duplicating domain logic from `oldaplib` unless it is
  specifically shaping HTTP response contracts.
- `oldap_api/imports` owns the cross-service ZIP import workflow. Canonical job
  JSON plus indexed ownership/version/quota facts are stored in the dedicated
  `urn:oldap:import-jobs` GraphDB graph; no SQL database or broker is added.
  Public import targets accept HTTP(S) IRIs and the canonical `urn:uuid` IRIs
  generated for OLDAP resource instances; local-file, executable, and other URI
  schemes remain outside the closed input boundary. Custom import SPARQL
  resolves the project's absolute data-graph IRI from its OLDAP namespace,
  uses the canonical HTTPS Schema.org vocabulary, and recognizes asserted
  project-specific subclasses of `shared:StagingArea`; it never depends on a
  request-local QName context or GraphDB reasoning. Transactional project
  authorization matches `oldap:projectShortName` as `xsd:NCName`, consistent
  with the OLDAP admin model, so RDF literal typing cannot cause a false
  permission revocation at commit time.
  Lifecycle mutations are immutable value transformations followed by one
  optimistic GraphDB transaction. Public views never persist or return a user
  access token, and direct upload tokens use `typ=ingest-upload`, audience
  `oldap-media-ingest`, and `OLDAP_IMPORT_UPLOAD_JWT_SECRET`.
  The staging batch intentionally uses direct, closed SPARQL generation rather
  than `ResourceInstance.create()`, because the latter owns a transaction per
  resource and cannot provide the required all-resources-plus-job boundary.
- MediaObject lookup endpoints expose the shared media access contract returned
  by `oldaplib`, including `shared:mediaAccessMode` plus optional external
  `shared:mediaUrl` and `shared:thumbnailUrl`.
- Password reset is handled by unauthenticated auth endpoints:
  `POST /admin/auth/password-reset/request` accepts either `userId` or `email`,
  records `oldap:passwordResetRequestAt`, creates a two-hour JWT reset link, and
  sends it by the configured mail backend; `POST /admin/auth/password-reset/confirm`
  validates the JWT against the current request timestamp, changes the password,
  and clears the timestamp.
- Password reset service configuration is environment-based:
  `OLDAP_PASSWORD_RESET_ADMIN_USER`, `OLDAP_PASSWORD_RESET_ADMIN_PASSWORD`,
  `OLDAP_PASSWORD_RESET_FRONTEND_URL` or `OLDAP_PUBLIC_APP_URL`, and
  `OLDAP_PASSWORD_RESET_JWT_SECRET`. Mail delivery defaults
  to console logging and uses SMTP when `OLDAP_PASSWORD_RESET_EMAIL_BACKEND=smtp`.
- `oldap_api.mail` is the shared console/STARTTLS SMTP transport. Password reset
  retains its existing content and backend variable; ZIP imports use
  `OLDAP_IMPORT_EMAIL_BACKEND` with the same `OLDAP_MAIL_*` connection settings.
  Import mail state is independent from lifecycle state, uses at most three
  submission attempts, and exposes no SMTP error text publicly.
- Public `GET /imports/{id}/report` authorizes job ownership before
  `ImportRecordClient` retrieves the retained JSON from media. A dedicated
  `typ=import-records` token and exact stored SHA-256 protect the internal hop;
  the browser receives neither that token nor an unverified report.
- Reset messages are UTF-8 multipart mail with plain-text and HTML alternatives.
  JWT separators are percent-encoded in the query parameter so mail-client link
  detection cannot truncate the token; the HTML alternative provides an
  explicit reset button and a complete copyable fallback URL.
- `python -m oldap_api.smtp_test` provides an interactive, credential-safe SMTP
  deployment diagnostic using the same mail environment variables. It tests
  STARTTLS, implicit TLS, or plain SMTP independently of OLDAP user data.
- Access/refresh configuration uses `OLDAP_ACCESS_JWT_SECRET`,
  `OLDAP_REFRESH_JWT_SECRET`, optional TTL/issuer/audience settings,
  `OLDAP_AUTH_ADMIN_USER/PASSWORD`, refresh-cookie settings, and optional exact
  `OLDAP_AUTH_ALLOWED_ORIGINS`. The retired `OLDAP_JWT_SECRET` is not accepted.
- Native mobile authentication is a transport-only addition. It reuses
  `TokenCodec`, access/refresh claims, lifetimes, signing keys, and `authVersion`
  semantics unchanged; it adds no server session, refresh rotation, or replay
  persistence and never returns the deprecated browser `token` alias.
- Local MediaObject lookup responses use `oldaplib` to issue one-hour
  `typ=media` capability tokens with audience `oldap-api-media` and
  `OLDAP_MEDIA_JWT_SECRET`. The media deployment must validate those tokens with
  the same media key; it uses the separate access key only for upload Bearer
  credentials.
- Local `make run`, `make run-prod`, and `make docker-run` load authentication
  values from an ignored `.env.local`; `.env.local.example` documents the
  required names without embedding usable credentials in Git.

## Current Conventions

- Code and documentation inside the repository are written in English.
- User communication is in German unless explicitly requested otherwise.
- Keep changes focused and follow existing Flask blueprint patterns.
- Public API changes should update `API-def/oldap-api.yaml` and relevant tests.

## Roadmap / Next Steps

- Start ZIP import Phase 3 in `oldap-mediaserver`: direct immutable SIP ingress,
  quarantine storage, upload-capability enforcement, and the durable SIP-stored
  callback. Migrate existing staging areas with `shared:stagingQuotaBytes`
  before deploying Shared ontology 0.6.0.
- Expose `/mobile/v1/auth/*` through the deployment proxy over TLS and align the
  exact CORS allowlist with the HTTP transport selected by Fasnacht Capture.
- Release and deploy the `oldaplib` archive-tree service before enabling the
  archive move endpoint in FasnachtsPage; the route returns `503` when an older
  library build is installed.
- Complete authentication roadmap work package 6 in the browser clients.
- Keep instance read responses stable while exposing reasoning-derived metadata
  explicitly.
- Continue consolidating duplicated instance-read logic when broader refactoring
  is warranted.
