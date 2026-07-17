# OLDAP API

## Running the API

### Environment variables that must be defined

- OLDAP_TS_SERVER (e.g. "http://localhost:7200")
- OLDAP_TS_REPO (e.g. "oldap") 
- OLDAP_API_PORT (e.g. "8000")
- OLDAP_REDIS_URL (e.g. "redis://localhost:6379")

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

2. Generate four independent random secrets. Run the following command four
   times and copy one different result into each JWT variable in `.env.local`:

   ```bash
   openssl rand -hex 32
   ```

   ```dotenv
   OLDAP_ACCESS_JWT_SECRET=<first generated value>
   OLDAP_REFRESH_JWT_SECRET=<second generated value>
   OLDAP_MEDIA_JWT_SECRET=<third generated value>
   OLDAP_PASSWORD_RESET_JWT_SECRET=<fourth generated value>
   ```

   Each value must contain at least 32 bytes. Access, refresh, and media secrets
   must be different; keeping the password-reset secret separate as well limits
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

4. Keep the template's development cookie and frontend settings when the local
   frontend runs at `http://localhost:5173`:

   ```dotenv
   OLDAP_AUTH_ALLOWED_ORIGINS=http://localhost:5173
   OLDAP_REFRESH_COOKIE_SECURE=false
   OLDAP_REFRESH_COOKIE_SAMESITE=Lax
   OLDAP_PASSWORD_RESET_FRONTEND_URL=http://localhost:5173
   OLDAP_PASSWORD_RESET_EMAIL_BACKEND=console
   ```

   `OLDAP_REFRESH_COOKIE_SECURE=false` is only appropriate for local HTTP
   development. With the console email backend, password-reset links are written
   to the API log instead of being sent by email.

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
