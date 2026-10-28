# Native Jena development environment

## Current scope

The migration worktrees live in `/Users/rosenth/ProgDev/OLDAP-Jena`.
Both repositories have Python 3.13 environments; the API installs its sibling
library as an editable Poetry dependency. Fuseki, API authentication, API port
isolation and backend compatibility are not configured yet. Do not start the API
or run the GraphDB integration suite as a Jena acceptance test.

## Redis

One additional native Redis process listens only on `127.0.0.1:6381`:

- Database 0: disposable object cache.
- Database 1: persistent writer coordination.
- AOF enabled, `appendfsync always`, `maxmemory-policy noeviction`.
- Both databases share process lifecycle and durability settings. Never use
  `FLUSHALL`; cache operations must target database 0 only.

Private runtime files are under
`/Users/rosenth/Library/Application Support/OLDAP-Jena/redis/`:
`redis.conf` (contains the generated password), `data/`, `redis.pid`, `redis.log`.
The directory is mode 0700 and the configuration is mode 0600.
The API's ignored `.env.local` (mode 0600) contains only the two Redis URLs:
`OLDAP_REDIS_URL` and `OLDAP_STAGING_LOCK_REDIS_URL`.
Do not commit these credentials or copy the original environment's credentials.
Library commands need these variables explicitly loaded; Python does not load
`.env.local` automatically.

Start manually (no launchd job or login autostart is installed):

```sh
/opt/homebrew/bin/redis-server \
  "/Users/rosenth/Library/Application Support/OLDAP-Jena/redis/redis.conf"
```

Check status from the Jena API repository without exposing credentials:

```sh
.venv/bin/python - <<'PYTHON'
from dotenv import dotenv_values
from redis import Redis
settings = dotenv_values('.env.local')
for name in ('OLDAP_REDIS_URL', 'OLDAP_STAGING_LOCK_REDIS_URL'):
    client = Redis.from_url(settings[name])
    print(name, client.ping())
PYTHON
```

To stop, first quiesce all Jena writers. Then run from the Jena API repository:

```sh
.venv/bin/python - <<'PYTHON'
from dotenv import dotenv_values
from redis import Redis
settings = dotenv_values('.env.local')
Redis.from_url(settings['OLDAP_STAGING_LOCK_REDIS_URL']).shutdown()
PYTHON
```

Do not use `make restart` or `make services-stop/start` for this instance:
those existing controllers address the original OLDAP services. The original
Redis processes on 6379 and 6380 are independent and were not changed.
`make run` and `make run-prod` now honor the configured cache URL, but still have
GraphDB/API endpoint defaults; completing Redis setup does not make those targets
ready for a separate Jena API.

## Verification

Authenticated PING, unauthenticated rejection, separate database visibility,
required persistence configuration, WAITAOF acknowledgement and test-key survival
across a graceful Redis restart passed. The temporary key was removed; both Jena
databases were empty afterwards. Original Redis PIDs remained unchanged.
