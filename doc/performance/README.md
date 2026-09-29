# Interactive read performance

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
