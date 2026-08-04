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
  the ontology validation and GraphDB transaction to `oldaplib`.
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
