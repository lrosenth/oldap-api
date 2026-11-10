# Native Jena development from OLDAP

The active checkout is `OLDAP/oldap-api`, with editable sibling `OLDAP/oldaplib`.
The installed macOS LaunchAgents use this checkout's `.venv` and private
`.env.local`. No active native service path depends on the OLDAP-Jena checkout.
The copied Java service was verified against all current Java source hashes.

## Daily commands

```sh
make services-status
make services-stop
make services-start
make restart
```

Stop terminal frontends with Ctrl+C before stopping services. Start them again
with their normal `npm run dev`. Finish uploads/imports/exports before stopping
or restarting the API. No stale writer ownership is cleared by these commands.

`OLDAP_BACKEND=jena` selects the new native service controller. GraphDB settings
continue to select the retained legacy controller. The Jena controller validates
that the API and identity LaunchAgents reference the exact environment and
checkout before making changes. A local flock serializes start/stop/restart;
interrupted operations retain the exact Docker resume IDs for recovery.

Startup order is existing local Redis services, Jena Redis, independent identity,
Jena, API, then previously running Docker containers. Stop closes Docker consumers,
API, Jena, identity and Redis, then Docker Desktop. Jena handles SIGTERM by draining
requests, aborting a remaining transaction and closing TDB. No forced TDB kill or
dataset deletion is performed. Docker shutdown includes ALL local Desktop
containers, preserving the owner's previous music/development workflow.
Missing saved container IDs stop restoration rather than substituting same-name
containers. Docker volumes/images are never deleted. Repeat stop is idempotent;
external restarts require `services-start` before another stop.

`make restart` replaces only the API and waits for readiness, leaving Java,
identity and Redis alive. Python source changes need this restart. A failure is
reported; inspect logs and use `services-start` to restore dependencies.

## Native runtime

Private directory: `~/Library/Application Support/OLDAP/local-jena/` (0700).
Environment/properties/Redis configuration files are 0600 and never committed.

| Service | LaunchAgent | Loopback endpoint |
| --- | --- | --- |
| Jena/TDB + managed Lucene | org.oldap.jena | 127.0.0.1:3031 |
| Token identity callback | org.oldap.jena-identity | 127.0.0.1:8001 |
| API | org.oldap.api | 127.0.0.1:8000 |
| Jena Redis | org.oldap.jena-redis | 127.0.0.1:6381 |

Jena uses installed JDK 25 and a 4 GiB maximum heap. Redis has authenticated
loopback access, AOF with `appendfsync always`, no eviction, cache database 0 and
coordination database 1. Never issue FLUSHALL. Existing Redis services used by
local media remain independently configured and are included in lifecycle control.

`native_service.py` loads the private environment and executes Gunicorn. Identity
reuses `OLDAP/oldap-setup/scripts/jena_identity.py`; it never starts the full API.
Logs are `<LaunchAgent label>.stdout.log` / `.stderr.log` in the private runtime.
Email backends are console-only. Existing local media integration settings are
retained; this operation copied the RDF dataset, not a fresh full media tree.

## Data source, rollback and verification

The separate dataset comes from the offline-consistent home snapshot
`20261108-operations-acceptance`, copied on 2026-11-10. API archive SHA-256:
`1b055475172e696e6fae85576ccfa3c5270b42e397fa5392d1d826ed92bfa1e4`.
The archive was verified before extracting only regular dataset files/directories;
links/path escapes are rejected. This is the November 8 snapshot, not ongoing
synchronization with home. Home itself was not stopped or modified.

Jena transport keys and Redis credentials are newly generated. Authentication
service credentials match the copied dataset; existing local JWT/media settings
remain local. The API environment is deliberately not a copy of home deployment
URLs or SMTP configuration. The old GraphDB database was not removed. Its agent
is disabled, with original API/GraphDB plists and `.env.local` retained in
`before-jena/`. Legacy Docker resume state also remains in OLDAP/writer-recovery.

For rollback, first stop Jena services, retain current dataset/runtime state,
restore the original environment and LaunchAgents from `before-jena/`, then use
the legacy `services-start`. Local Jena writes are not merged back into GraphDB;
never overwrite either dataset as part of a service rollback.

Acceptance: 15 controller/restart tests pass; real stop/status/start completes,
Docker resumes its saved containers, anonymous login and configured-account login
return 200, and a public archive search returns ten rows after restart. No home
or production write and no local upload/import acceptance is claimed.

Poetry installation may replace the editable library with the locked PyPI wheel.
To resume editing the sibling library, run `.venv/bin/python -m pip install
--no-deps -e ../oldaplib`, then `make restart`. Packaging/release builds continue
using the locked/reviewed release workflow, independent of the local editable
installation.
