# Local development and music mode

Run these targets from `oldap-api`. They control the reviewed native MacBook
installation; they are not production deployment commands.

| Command | Purpose |
| --- | --- |
| `make restart` | Reload API/oldaplib Python code by restarting only the API. |
| `make services-stop` | Stop API, GraphDB, writer Redis, cache Redis, all running Docker containers and Docker Desktop. |
| `make services-start` | Start Redis/GraphDB/API in dependency order, then Docker Desktop and the previously running containers. |
| `make services-status` | Show native job and Docker Desktop state. |

Before music, finish uploads/imports/exports and stop each frontend's `npm run dev`
with Ctrl+C. Then run `make services-stop`. Before developing, run
`make services-start` and start the frontends in their terminals as usual.

Stop holds the normal writer gate while stopping containers/API/GraphDB. An active
or retained writer refuses this operation before anything is stopped. After those
backends end, the gate is released normally and both Redis services stop. No lock
reset, data deletion, image rebuild or volume removal occurs. Failed/uncertain
backend control retains the gate for operator inspection; start can bring back
services for diagnosis without clearing it.

Native LaunchAgents are disabled as well as unloaded, so KeepAlive/login cannot
restart them. Start enables them again. Docker's own login-item preference remains
unchanged: check status or stop again when entering music mode after a new login.
The Desktop CLI can wait/fail when queried after complete application exit; the
helper detects the absence of the installed Docker application/backend processes
before making that RPC. Its small privileged networking helper is left to macOS.
All container commands explicitly address the local Desktop Unix socket, regardless
of the user's selected remote Docker context.

A private resume list stores the exact previously running container IDs under
`~/Library/Application Support/OLDAP/writer-recovery/development-state.json`.
A local file lock serializes start/stop commands. Repeated stop is harmless;
external restarts are reported. Missing/replaced containers are not silently
recreated. On a partial failure, retain the resume file and use
`make services-start` to restore dependencies; unresolved writer ownership still
requires the regular recovery procedure.

Frontends, IDEs, Jupyter, sync apps and other native applications remain manual.
This is a development-service switch, not a guarantee of real-time audio latency.
Fast user switching also leaves applications in the previous login session running.

Implementation: `development_services.py`, shared inventory validation in
`restart_api.py`. User-facing usage and scope are documented directly in Makefile.
See `development-services-verification.json` for the local stop/start acceptance.
