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
| Official Fuseki console proxy | org.oldap.jena-console | 127.0.0.1:3030 |
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

## Official local Fuseki console

Open **http://127.0.0.1:3030** (use this exact host). Username/password are the
same operator credentials as fuseki.home.org, read from the protected
`~/.config/oldap/home-console-test.json` during installation. No password or
internal administrator key is committed or passed on the command line.

The unmodified Apache 6.2.0 UI is served by the same native Jena JVM and dataset.
Its optional administrator listener is bound to 127.0.0.1:8040 and requires a
separate private header key. A native Homebrew Caddy proxy on 127.0.0.1:3030 adds
that key after HTTP Basic authentication. Foreign Host names do not select the
proxy; write requests require the exact local Origin. The Java service permits
HTTP origins only with explicit `adminLoopback=true` and host 127.0.0.1. Existing
server deployments retain their HTTPS requirement/default listener behavior.
`/_ready` is an unauthenticated loopback-only ping, not dataset access.

Queries, SPARQL updates and uploads operate directly on the local dataset; they
bypass OLDAP model validation and resource permissions. Dataset creation/deletion,
compaction and backups remain service/operator workflows. There is no second TDB
process and no connection to home or production data.

The optional org.oldap.jena-console LaunchAgent is included automatically once
installed. It starts after API/Jena readiness and stops before the API/Jena.
`make restart` still replaces only the API. Native console logs and configuration
are in the private local-jena runtime. Caddy was installed with Homebrew, but its
service is managed by OLDAP, not `brew services start caddy`.

To reproduce installation after building and accepting a Jena distribution with
loopback administration support:

```sh
make services-stop
.venv/bin/python configure_local_console.py \
  --distribution "$HOME/Library/Application Support/OLDAP/local-jena/service-console" \
  --credentials "$HOME/.config/oldap/home-console-test.json"
make services-start
```

The installer validates proxy syntax and JAR hash, refuses occupied native ports,
and preserves earlier private configuration under `before-console-TIMESTAMP`.
The installed artifact is `service-console`; original `service` is retained.
This is a local development artifact, not a newly published 1.0.1 release.
To roll back, stop services, remove the console LaunchAgent, restore the prior
Jena plist/service.properties from that backup and start services. Do not restore
or delete the dataset. The service controller then omits the absent console.

Acceptance on 2026-11-10: 20 native HTTPS checks, 22 native loopback checks
(including rejection of HTTP without loopback and of foreign HTTP origins),
15 controller/installation tests; official UI bytes match the Apache JAR. Local
query, native update/readback/cleanup, denied anonymous/cross-origin requests,
loopback socket bindings and a complete Make stop/status/start cycle pass.
Poetry's launcher was also repaired to use installed Homebrew Python 3.14.8 after
its old interpreter path proved unavailable; application virtualenvs were retained.
