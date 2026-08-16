# OLDAP ZIP export v1 contracts

This directory is the v1 contract source for project-neutral OLDAP Staging and
Archive ZIP exports. Public Staging and Archive estimate/job creation plus the
shared listing, cancellation, and download-capability endpoints are implemented.
The JWT-protected internal
worker claim/heartbeat/manifest/result/cleanup endpoints are also implemented.
READY/FAILED outbox delivery, automatic READY expiry, cleanup selection, and
60-day audit-hull pruning are implemented. The paired media-local ZIP
builder/storage is implemented. The Archive projector reads only requester-visible
units and profile-permitted media, preserves deduplicated relationships, resolves
visible labels, and rechecks profile, unit, media, and link visibility before
download capability issuance. ArchiveTree UI actions remain outstanding.

## Architectural boundary

- `oldap-api` authenticates the requester, resolves the project, authorizes
  every visible resource, applies the trusted project profile, freezes the
  canonical manifest, owns jobs/leases/email/audit, and issues capabilities.
- A media-local worker receives only the canonical manifest. It does not query
  OLDAP, interpret ontology properties, or execute project code.
- The media service stores private partial/final export artifacts, authorizes
  exact downloads, supports cleanup, and leaves normal asset delivery intact.
- Project profiles may add declarative metadata projections and allowed archive
  media subclasses. They cannot change selection, authorization, paths,
  checksums, lifecycle, credentials, limits, or binary access.

## Runtime profile registry

Runtime profiles are server-owned JSON files named
`<project-short-name>.json`. The bundled `fasnacht-v1` profile lives in
`oldap_api/exports/profile_data`; another deployment may set
`OLDAP_EXPORT_PROFILE_DIR` to an absolute profile directory. The registry
validates both the closed profile contract and the requested project/profile
identity. Profile files are never selected by a browser path.

Creating an export containing local originals requires
`OLDAP_EXPORT_SERVICE_JWT_SECRET` for the API-to-media source resolver. Issuing
a READY download capability additionally
requires the distinct `OLDAP_EXPORT_DOWNLOAD_JWT_SECRET`. Deployments must not
reuse either key for another trust boundary.

Internal worker calls use `typ=export-service` and audience
`oldap-api-export-service`. The API reads the job graph through the dedicated
non-token-issuing `OLDAP_EXPORT_SERVICE_USER` and
`OLDAP_EXPORT_SERVICE_PASSWORD`. Claims are renewable, results are idempotent,
and successful cleanup atomically deletes the frozen manifest and redacts the
selection path/IRI from the retained 60-day audit record.

READY and FAILED results atomically persist a notification marked `PENDING`.
`OLDAP_EXPORT_EMAIL_BACKEND=console|smtp` selects the shared mail transport;
`OLDAP_PUBLIC_APP_URL` supplies a token-free `/exports/{exportId}` status link.
Submission is independent from lifecycle state and is attempted at most three
times with five-minute backoff. Worker polling also moves elapsed READY jobs
through EXPIRED into claimed cleanup and removes already content-free DELETED
audit hulls only after their 60-day deadline.

## Versioned artifacts

- `export-profile.schema.json`: closed server-owned profile configuration.
- `manifest.schema.json`: immutable API-to-worker snapshot.
- Archive manifests carry an exact `archiveUnits` inventory; the generic media
  worker writes it as `archive-units.csv` without interpreting ontology terms.
- `examples/fasnacht-v1.profile.json`: first production-facing profile.
- `examples/museum-v1.profile.json`: non-Fasnacht generics proof.
- `examples/metadata.csv`: normative CSV encoding example.

All JSON artifacts use UTF-8. Digests use lower-case SHA-256 over RFC 8785
canonical JSON. CSV uses UTF-8 with BOM, RFC 4180 quoting, a stable profile-
versioned column order, and JSON text for multi-valued cells. Spreadsheet
formula prefixes are neutralized in human-facing scalar cells.

## Approved operating values

- Maximum produced archive: configurable 50,000,000,000 bytes per job.
- READY retention: 24 hours.
- Content-free job audit retention after artifact deletion: 60 days.
- Minimum data permission: `DATA_VIEW`, checked per resource.
- Oversized selections are split by deliberate additional subtree exports;
  v1 never creates an implicit multipart ZIP set.

## Phase 0 acceptance

The same parser and contract tests must accept both example project profiles.
No `fasnacht:` identifier may occur in the generic domain, manifest schema,
job state, worker protocol, media route, or capability claims.
