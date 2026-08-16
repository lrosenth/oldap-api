# OLDAP API

## Running the API

### Environment variables that must be defined

- OLDAP_TS_SERVER (e.g. "http://localhost:7200")
- OLDAP_TS_REPO (e.g. "oldap") 
- OLDAP_API_PORT (e.g. "8000")
- OLDAP_REDIS_URL (e.g. "redis://localhost:6379")
- OLDAP_IMPORT_UPLOAD_JWT_SECRET (a dedicated random value of at least 32 bytes)
- OLDAP_IMPORT_SERVICE_JWT_SECRET (a second dedicated random value of at least 32 bytes)
- OLDAP_IMPORT_RECORDS_JWT_SECRET (dedicated API-to-media retained-record key)
- OLDAP_MEDIA_INGEST_URL (e.g. "https://media.oldap.org")
- OLDAP_MEDIA_INTERNAL_URL (optional API-to-media URL; defaults to `OLDAP_MEDIA_INGEST_URL`)
- OLDAP_IMPORT_SERVICE_USER and OLDAP_IMPORT_SERVICE_PASSWORD (dedicated GraphDB-facing OLDAP service identity)

ZIP import jobs additionally require every participating
`shared:StagingArea` to define a positive `shared:stagingQuotaBytes` value.
If a restored legacy StagingArea has no quota, job creation returns
`503 IMPORT_QUOTA_NOT_CONFIGURED` rather than reporting the otherwise valid
staging target as missing.
The upload JWT secret is accepted only for short-lived direct SIP-upload
capabilities and must differ from access, refresh, media, and password-reset
keys.

Import reports are retrieved from `OLDAP_MEDIA_INTERNAL_URL` with
`OLDAP_IMPORT_RECORDS_JWT_SECRET`; the internal URL defaults to the public
`OLDAP_MEDIA_INGEST_URL` when no separate server-to-server route is required.
The records key must also be configured on the media records service and is
never returned to clients. Import notification delivery
uses `OLDAP_IMPORT_EMAIL_BACKEND=console|smtp` and the same `OLDAP_MAIL_*` SMTP
settings as password reset. `OLDAP_PUBLIC_APP_URL` supplies the authenticated,
token-free job link included in those messages.

ZIP-export completion notifications use the parallel
`OLDAP_EXPORT_EMAIL_BACKEND=console|smtp` switch and the same mail transport.
New export jobs use the bounded deployment policy from
`OLDAP_EXPORT_MAX_ARCHIVE_BYTES` (default and hard ceiling 50 GB),
`OLDAP_EXPORT_READY_RETENTION_HOURS` (default 24, maximum 744), and
`OLDAP_EXPORT_AUDIT_RETENTION_DAYS` (default 60, maximum 3650). Invalid values
fail closed when an export endpoint or worker claim is handled. A frozen
manifest retains the limit selected when its job was created.
Creation also reserves project-neutral capacity atomically. The defaults are
three active jobs and 100 GB retained source bytes per user, plus twenty active
jobs and 500 GB retained source bytes system-wide. Override them with
`OLDAP_EXPORT_MAX_ACTIVE_JOBS_PER_USER`, `OLDAP_EXPORT_MAX_ACTIVE_JOBS_TOTAL`,
`OLDAP_EXPORT_MAX_RESERVED_BYTES_PER_USER`, and
`OLDAP_EXPORT_MAX_RESERVED_BYTES_TOTAL`. Reservations remain until physical
cleanup reaches `DELETED`.
READY and FAILED transitions persist their notification outbox state atomically;
delivery failures are retried at most three times with five-minute backoff.
`OLDAP_PUBLIC_APP_URL` produces `/exports/{exportId}` links without embedding a
download capability.

Import list responses use an opaque `nextCursor`; clients must return it
unchanged with the same state filter. Accepted lifecycle mutations emit a
privacy-preserving operational audit line containing only event, import ID,
state/version, and sanitized request ID. Filenames, tokens, claims, checksums,
and report contents are intentionally excluded from logs.

The internal sequential queue supports `VALIDATE`, `IMPORT`, and `CLEANUP`.
Cleanup eligibility is API-owned: stale `UPLOADING` jobs after 24 hours,
persisted-expiry `READY` jobs, and `cleanupPending` terminal jobs may be leased;
`IMPORTING` is never eligible. `POST /internal/imports/{importId}/cleanup-result`
accepts deletion proof idempotently. Only that accepted proof can mark expiry
and release an expired reservation; an `IMPORTED` job retains its extracted-byte
quota because its staged originals remain stored.
Pending or failed import email is reconciled only by the API during an idle
ingest-worker poll. At most one due notification is attempted per poll, no more
than three times total, and failed attempts are spaced by at least five minutes.
This keeps SMTP credentials and recipient resolution out of the media worker
and prevents mail delivery from consuming an active task lease.

The generic instance transformation endpoint accepts an optional `linkFrom`
object with `resourceIri` and an object-property QName. OLDAP validates the
source shape and target range, requires `DATA_UPDATE` on the source resource,
and commits the relation and class transformation atomically. This is used by
Staging-to-Archive publishing to add `shared:ArchiveUnit` →
`shared:hasMediaObject` without exposing a partial transform state.

To run, issue the command

```bash
poetry run gunicorn oldap_api.wsgi:app -b 127.0.0.1:${OLDAP_API_PORT} --workers 2 --threads 2 --timeout 60 --access-logfile - --error-logfile -
```

## Testing with "make run"

`make run` starts the API directly through Poetry and loads authentication
configuration from `.env.local`. This file is ignored by Git and must never be
committed.

1. Create the local configuration from the non-secret template:

   ```bash
   cp .env.local.example .env.local
   ```

2. Generate seven independent random secrets. Run the following command seven
   times and copy one different result into each JWT variable in `.env.local`:

   ```bash
   openssl rand -hex 32
   ```

   ```dotenv
   OLDAP_ACCESS_JWT_SECRET=<first generated value>
   OLDAP_REFRESH_JWT_SECRET=<second generated value>
   OLDAP_MEDIA_JWT_SECRET=<third generated value>
   OLDAP_PASSWORD_RESET_JWT_SECRET=<fourth generated value>
   OLDAP_IMPORT_UPLOAD_JWT_SECRET=<fifth generated value>
   OLDAP_IMPORT_SERVICE_JWT_SECRET=<sixth generated value>
   OLDAP_IMPORT_RECORDS_JWT_SECRET=<seventh generated value>
   ```

   Each value must contain at least 32 bytes. All seven secrets must be different;
   keeping every token purpose cryptographically separate limits
   the impact of a leaked key. Keep these values stable between local restarts,
   because replacing them invalidates tokens signed with the previous values.

3. Set the service credentials in `.env.local` to a real active OLDAP user that
   has sufficient permission to read and update users in the local GraphDB data:

   ```dotenv
   OLDAP_AUTH_ADMIN_USER=<local OLDAP administrator user ID>
   OLDAP_AUTH_ADMIN_PASSWORD=<that user's password>
   OLDAP_PASSWORD_RESET_ADMIN_USER=<local OLDAP administrator user ID>
   OLDAP_PASSWORD_RESET_ADMIN_PASSWORD=<that user's password>
   ```

   For a local setup, both service roles may use the same administrator account.
   The authentication credentials are used by refresh and logout; the
   password-reset credentials are used by the reset endpoints. They are not JWT
   secrets and must match a user in the loaded local OLDAP data.

4. Keep the template's development cookie and frontend settings aligned with
   every exact local frontend origin. FasnachtsPage normally uses local HTTPS
   on ports 5173 or 5174; the HTTP variants are retained for optional plain-HTTP
   Vite sessions:

   ```dotenv
   OLDAP_AUTH_ALLOWED_ORIGINS=https://localhost:5173,https://localhost:5174,http://localhost:5173,http://localhost:5174
   OLDAP_REFRESH_COOKIE_SECURE=false
   OLDAP_REFRESH_COOKIE_SAMESITE=Lax
   OLDAP_PASSWORD_RESET_FRONTEND_URL=https://localhost:5173
   OLDAP_PASSWORD_RESET_EMAIL_BACKEND=console
   ```

   Set `OLDAP_REFRESH_COOKIE_SECURE=true` when testing refresh cookies through
   local HTTPS. `false` is only appropriate for an explicitly selected local
   HTTP session. With the console email backend, password-reset links are
   written to the API log instead of being sent by email.

5. Ensure GraphDB is available at `http://localhost:7200`, the `oldap`
   repository contains the required OLDAP data, and Redis is available at
   `redis://localhost:6379`. Then start the API:

   ```bash
   make run
   ```

The API listens on `http://localhost:8000`. A missing `.env.local` is reported
before startup. Configuration errors for missing, too-short, or reused JWT
secrets are reported when the corresponding authentication or media operation
is used.

## Testing production SMTP delivery

The SMTP diagnostic uses the same `OLDAP_MAIL_*` variables as password-reset
delivery and sends one plain-text test message. Run it interactively inside the
deployed API container so that the container's DNS, firewall, TLS trust store,
and environment are tested as well:

```bash
docker exec -it oldap-api python -m oldap_api.smtp_test
```

Existing environment values are offered as defaults. The password is read with
terminal echo disabled and is never accepted as a command-line argument. Use
`starttls` to exercise the transport currently implemented by the API (normally
port 587). The diagnostic also supports `ssl` for providers that require
implicit TLS (normally port 465), but the password-reset mailer itself does not
currently implement that mode.

To test an existing container before rebuilding the image, copy only the
standalone module from a checkout on the production host and execute it from
the container's temporary directory:

```bash
docker cp oldap_api/smtp_test.py oldap-api:/tmp/oldap_smtp_test.py
docker exec -it oldap-api python /tmp/oldap_smtp_test.py
```

For a non-interactive check, provide the recipient through the environment and
use the deployed mail settings:

```bash
docker exec \
  -e OLDAP_SMTP_TEST_RECIPIENT=recipient@example.org \
  oldap-api python -m oldap_api.smtp_test --non-interactive
```

A successful result means the SMTP server accepted the message for delivery;
confirm final delivery in the recipient inbox or spam folder. Avoid shell debug
tracing while handling mail credentials.
