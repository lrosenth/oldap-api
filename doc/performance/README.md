# Interactive read performance

The deployed project-identity optimization is verified in
[2026-10-01-vm-project-identity.md](2026-10-01-vm-project-identity.md).

The local project-identity projection and repeated source comparison are in
[2026-10-01-project-identity.md](2026-10-01-project-identity.md).

The released optimization's VM before/after comparison is in
[2026-10-01-vm-serializer.md](2026-10-01-vm-serializer.md).

The constructor-metadata optimization and controlled local comparison are in
[2026-09-30-serializer.md](2026-09-30-serializer.md).

The deployed Docker VM acceptance and read measurements are in
[2026-09-30-vm.md](2026-09-30-vm.md).

The separate Gunicorn 1/2/4-worker comparison and startup changes are in
[2026-09-30-workers.md](2026-09-30-workers.md).

The mixed-reader concurrency results and next worker experiment are in
[2026-09-30-load.md](2026-09-30-load.md).

The implemented optimizations and before/after results are in
[2026-09-29-optimization.md](2026-09-29-optimization.md).

The first completed baseline and recommendations are in
[2026-09-29-baseline.md](2026-09-29-baseline.md).

`tools/read_performance.py` measures existing Fasnacht data sequentially, using
the native API runtime. Its purpose is bottleneck attribution, not load testing
or production sizing. No framework, library or database tuning is applied.

## Execution

From the API repository, use the Python interpreter in the `org.oldap.api`
LaunchAgent (verify the path on the current machine):

```sh
/Users/rosenth/Library/Caches/pypoetry/virtualenvs/oldap-api-69wuW7M7-py3.13/bin/python tools/read_performance.py --output /absolute/path/to/new-run --samples 12
```

The output directory must not already exist. `--discovery-only` inventories the
runtime and preflights cases without running repeated samples. The benchmark is
intentionally local and project-specific: repository `oldap`, API port 8000,
GraphDB port 7200, cache Redis port 6379/database 0. It loads `.env.local` without
printing secrets and uses the installed oldaplib, not the sibling source tree.
The unknown account is the primary subject; the configured service credentials
are also used only when their username is exactly `rosenth`, as authorized for
this baseline. Authentication/bootstrap is outside latency measurements.

`--case NAME` restricts the catalog and can be repeated. `--verify-only`
compares live/isolated response content without timed repetitions, normalizing
unordered RDF/model arrays and ignoring independently issued media JWT values.
Result IRI order is reported separately. For the supplemental run:

```sh
python tools/read_performance.py --output /absolute/path/to/new-supplement --samples 6 --case resource_media --case summaries_25 --case datamodel_fasnacht --case datamodel_shared --case search_lucene_fields
```

## Read boundary and lifecycle

- Requests are sequential and restricted to local query/metadata endpoints and
  the listed read routes. POST search and summary operations are reads.
- SPARQL Update, remote SERVICE and Lucene connector control are blocked. A
  validation copy substitutes RDF-star quoted terms because RDFLib's SPARQL
  parser does not understand them; the original ACL query is sent unchanged.
- GraphDB queries have a 15-second server timeout and a 20-second HTTP timeout;
  API HTTP calls have a 25-second timeout. No repository configuration changes.
- No app restart, cache flush, writer lock or integration-test fixtures. The
  isolated app uses `factory()` and matches the native launcher's `Dev` settings
  with debug disabled. It deliberately omits `create_app()` and its cache flush.
- Normal library cache population can occur. Caches are shared and not emptied;
  these are warm measurements, not cold-start measurements. Read-only traffic
  can still consume CPU, memory and cache capacity on the shared service.
- All explicit named-graph bindings are hashed in memory before/after the full
  run, including RDF-star bindings. Only the count and digest are retained.
  A mismatch stops successful completion; concurrent user writes would also
  cause a mismatch. This is not a transactionally isolated database snapshot.
- Only the benchmark process is instrumented. Monkey patches end with that
  process. The live API and installed library files remain unchanged.

## Measurement design

Each case and subject gets one discarded warmup followed by 12 serial samples
in three distinct modes:

1. `live_http`: unmodified running API over local HTTP, persistent client
   session; includes response transfer and client JSON decoding.
2. `inprocess`: uninstrumented Flask test client using the same API sources,
   configuration and installed dependency versions, without socket/server cost.
3. `instrumented`: the same test client, with nested wall-time spans for
   connection/authentication, model loading, cache materialization, library
   operations, GraphDB HTTP, RDF decoding, API shaping and JSON encoding.

The modes run sequentially, not interleaved, so differences also include noise
and cache/history effects. In-process timings include the test-client harness
and response JSON decoding. They are not an exact subtraction from live HTTP.
Before comparing modes, verify successful responses and equivalent payloads.

`inclusive_ms` includes child spans; `exclusive_ms` removes them. Exclusive
buckets partition instrumented request wall time without adding nested work
twice. `graphdb.http` includes local transport, GraphDB queue/evaluation and
response download. It is **not pure engine execution time**. RDF parsing and
cache object reconstruction occur outside that transport bucket. Exact query
hashes allow repeated query attribution; private `queries.json` provides the
corresponding SPARQL for follow-up diagnosis.

`cache.get` includes Redis access and Python deserialization, not just Redis
server work. The refined harness additionally records `redis.command` (including
connection establishment) and `redis.client_init`; subtract child spans before
attributing exclusive Python work. Cache hit/miss counts are collected independently. CPU profiles
are run separately after timing and must not be interpreted as latency samples.
Client-process CPU during `live_http` says nothing about API CPU usage.

Reported p95 is the nearest-rank sample percentile. With only 12 repetitions it
is effectively the maximum: useful for detecting variability, not a robust
production tail-latency estimate. Fixed objects and queries provide a repeatable
baseline; they do not reproduce a complete browser session or a mixed workload.

## Artifacts and validation

The private run directory contains inventories, case definitions, subject role
summaries, raw timings, aggregate timings, SPARQL queries and CPU profiles. No
tokens, credentials or API response bodies are saved. Query text and resource
identifiers can still be sensitive; do not publish the private directory.
The repository report contains only selected non-secret aggregates.

Offline checks (no database fixtures or network calls):

```sh
python -m unittest discover -s tools -p test_read_performance.py
```

Before subsequent strategy decisions, retain the same catalog and separate
unknown-user results from administrator results. Data growth, concurrency,
GraphDB Enterprise and FastAPI experiments are later work packages.


For an exact before/after replay, pass `--catalog /path/to/previous/cases.json`.
The harness records installed library source hashes, since unpublished local
wheels can retain a version number. After a fresh native API restart it performs
one ordinary anonymous login outside timings to populate process-local project
prefixes. The bootstrap creates no refresh session and writes no RDF data.

For a source-tree comparison, select the intended library through `PYTHONPATH`
and use `--mode inprocess --mode instrumented` to exclude timings from the
separately installed native API. Modes always execute in the standard order,
with instrumentation last. Inventory records the imported source version/path
and serializer hash separately from installed package-distribution metadata.
`--verify-only` records normalized response digests for cross-run comparisons;
tokens and complete payloads remain in memory. The temporary Gunicorn read
experiment also verifies a serializer-source hash returned by each test worker,
so an accidentally imported installed library cannot pass source acceptance.

## Mixed-user live load test

`tools/read_load.py` replays the saved reference catalog through the running API.
It does not construct a Flask app, restart services, clear caches, or change RDF.
Use the same native interpreter as above:

```sh
python tools/read_load.py --catalog /absolute/path/to/cases.json --output /absolute/path/to/new-load-run --seconds 60
python -m unittest discover -s tools -p 'test_read*.py'
```

Stages use 1, 2, 4, 8, 16 anonymous users, followed by one recovery user. Each
user has an independent HTTP session and executes sequential workflows with
seeded 0.5–1.5 second think times. The repeating workflow mix is 30% sorted
search plus 25 summaries, 30% resource opening, 20% archive navigation (children
plus linked resource), 10% structured full-text search, 5% datamodel retrieval,
and 5% hierarchical-list retrieval. Cases replay fixed reference resources;
search results are not dynamically fed into the next request. This gives a
reproducible hot-read workload, not a random sample of all content or UI traffic.
Login and one preflight of each case occur outside measured stages.

HTTP duration includes reading the response body but excludes JSON parsing and
content hashing. Workflow duration includes those client checks but excludes
think time. All responses must match preflight content after unordered-array
and capability normalization. Ordering is not checked. Process CPU is derived
from accumulated `ps` CPU time (100% = one core); RSS is sampled each second.
Throughput uses the whole stage including startup, drain and sampler completion,
so it is slightly conservative. Stages are separated by three seconds.

A response error/content mismatch or any request exceeding five seconds stops
new work; in-flight reads drain with bounded client timeouts. A stage p95 above
two seconds prevents further ramping. Neither threshold is a product SLA. These
limits protect the shared local service, but client timeouts do not cancel an
already executing server query. Explicit named-graph fingerprints are compared
before/after in a `finally` block. Artifacts include stage requests, workflows,
process samples and summary; credentials and response bodies are not persisted.

The ramp is closed-loop: slower responses reduce the offered request rate.
Do not interpret virtual users as simultaneous requests, maximum supported
users, or production capacity. No claim about larger datasets, cold caches,
WAN/media transfer, multi-process deployment, or Enterprise follows from it.

## Existing Docker VM measurement

`tools/read_vm.py` runs on the Linux Docker host with Python 3 and `requests`.
Copy it together with `read_load.py`, `read_performance.py` and the private
reference `cases.json` to a temporary directory accessible only to the operator.
No Poetry environment, application import, dependency installation, container
restart or configuration change is needed. Run:

```sh
python3 read_vm.py --catalog cases.json --output results --seconds 30
```

The script inspects the existing `oldap-api`, `graphdb` and `redis` containers,
uses the API's private Docker address, and samples every API/master/worker and
GraphDB/cache process through Linux `/proc`. Docker access and permission to
read those process statistics are required. Process/container changes invalidate
the comparison; these metrics include other traffic and background work.
The sampler selects the deployed `gunicorn`, `java` and `redis-server` processes;
transient healthcheck and `docker exec` helpers are excluded. A missing service
or a changed worker PID still fails acceptance, with expected/observed IDs in
the diagnostic. This prevents helper processes from masquerading as restarts.

The request boundary allows only exact catalog bodies on known read routes and
anonymous token issuance. Redirects and environment proxies are disabled. The
only direct database request is a fixed SELECT over explicit named-graph data,
before and after the run. No database credentials are loaded; a protected query
endpoint fails rather than attempting other authentication or configuration.
Existing data and permissions determine whether the catalog is usable. Missing
resources, non-200 responses or changed response content stop acceptance rather
than silently substituting a different workload.

Each of the 17 reference cases receives one discarded warmup and 12 measured
reads, followed by the same 1/2/4/8/16/1-reader workflow ramp. HTTP durations
exclude JSON parsing/content hashing; workload durations include them. Existing
latency/content stop rules apply. The fingerprint covers explicit named graphs,
not inferred statements, repository settings or an independent default graph.
Concurrent real-user writes can change it; a mismatch must be investigated,
never repaired automatically by this tool.

Keep raw files private, copy results back, then remove only the temporary run
directory created for this measurement. Publish aggregate metrics, never tokens,
response bodies or the private request catalog. VM measurements exclude public
TLS/proxy/WAN latency and must not be treated as a controlled before/after
comparison against a laptop with different data/hardware/thread settings.

## Separate Gunicorn worker experiment

`tools/worker_read_experiment.py` supervises temporary Gunicorn instances on
`127.0.0.1:8100`, comparing 1, 2 and 4 `gthread` workers with four threads each.
Run with the native API interpreter and the saved catalog:

```sh
python tools/worker_read_experiment.py --catalog /absolute/path/to/cases.json --output /absolute/path/to/new-worker-run --seconds 30
```

It loads the local private `.env.local` and the native loopback database/cache
settings. The existing API on 8000 remains running and is sampled as a peer.
The output directory must be new. Each worker must serve all eight workload
cases with a token issued outside the test instance, before any login reaches
that instance. Concurrent preflight clients ensure observed coverage rather than
assuming fair distribution of serial connections. This also warms every worker. A test-only Gunicorn hook rejects
all non-catalog HTTP operations and adds a worker PID header. It must never be
used as the production configuration. No `--preload` is used: application
initialization occurs independently in each worker.

The same workload runs for 1, 8, 16 and 1 recovery reader per configuration.
Every stage uses the chosen duration; stop rules from the ordinary load test
still apply. The supervisor terminates only its own Gunicorn process group,
waits for shutdown, and checks port release before moving to the next worker
count. Explicit RDF fingerprints bracket each load run and the whole experiment.
`--workers 4` can restrict a fresh run to one selected configuration.
Raw logs are private and no token or response body is deliberately persisted.

`read_load.py` also accepts `--api-url http://localhost:PORT` and `--users 1 8 16 1`.
For Gunicorn it records every listener PID, individual process CPU/RSS and
aggregate `api_total` CPU (master plus workers). Worker replacement during a
stage fails sampling rather than silently omitting the new worker. Per-response
worker identities allow inspection of keepalive distribution. Changing worker
count also changes total thread capacity; this measures a deployment choice,
not an isolated proof about the GIL. Closed-loop think time limits offered load.

## Worker startup and explicit cache invalidation

`create_app()` now preserves the shared object cache. Before readiness it uses
an ordinary anonymous library Connection to populate process-local project
prefixes, then discards that connection/token. Existing bearer tokens can
therefore reach any freshly initialized worker. Startup requires GraphDB and
the anonymous principal to be available. Authentication and mutable model
instances remain request-local; no user Connection is retained in app state.

An application restart is **no longer a cache invalidation operation**. When a
schema/model deployment or out-of-band GraphDB edit requires full invalidation:

1. Quiesce all API readers and writers using that cache, and prevent automatic
   restart/traffic until maintenance completes. The writer gate alone does not
   stop readers from repopulating stale cache entries.
2. In the exact reviewed runtime environment (database/cache/writer URLs and
   secrets), run `python -m flask --app oldap_api:create_app clear-object-cache`.
   This explicit command holds the existing writer gate with zero wait, refuses
   occupied/uncertain ownership, and relies on the library's cache/writer Redis
   separation check. It clears the object cache only; do not use Redis FLUSHALL.
3. Start workers and warm/verify reads. All processes should use matching library
   and model versions. Concurrent mixed-version rollout was not validated here.

The command is deliberately not run by the read benchmark. Existing selective
cache invalidation in normal writes is unchanged. Creating upload/tmp directories
is now race-safe when multiple processes start together.

The native launchd recovery operator explicitly requires foreground services
without child processes. These read-only Gunicorn experiments are outside its
writer inventory. They are not authorization to replace the native writer
service with Gunicorn: production multi-process write support requires its own
supervision/fencing/recovery lifecycle review and tests.

## Docker deployment follow-up

`oldap-setup` now exposes worker/thread counts through Ansible and has an isolated
real-API crash/replacement/recovery probe for two and four workers. Its existing
Docker recovery removes whole writer containers and therefore covers their worker
processes. The native macOS single-process restriction is separate and unchanged.
See sibling `oldap-setup/docs/api-workers.md` for configuration, maintenance and
acceptance limits. This does not automatically deploy the startup changes.
