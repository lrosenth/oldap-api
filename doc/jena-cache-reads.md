# Jena relationship reads with actual Redis

## Acceptance (2026-10-31)

The focused API runner now supports `--cache-only`. It starts its own socket-only
Redis using the existing owned-store context manager, selects DB 0 for object
cache and DB 1 for coordination, and starts a fresh Jena dataset and normal API.
No cache constructor/get/set/delete is mocked. No shared Redis is contacted or
cleared. All owned processes are stopped on completion or failure.

The fixture uses a modeled parent/child relation, a reader, an unrelated user,
and an independent owner role so the administrator can restore downgraded reader
permissions. It exercises class-filtered, projected, sorted relationship search,
count and detail endpoints. The cache stores shared model/project metadata;
these endpoints still query the current instance data and applicable grants.

The initial sequential run passed **17 focused HTTP checks** and **16 authentication/Redis configuration tests**. Repeated warm reads produce 45 additional Redis hits; 19 keys remain in the
owned cache at the end. This proves real cache use, not a mock returning misses.

Verified behavior:

- Shared cached metadata does not transfer visibility between users.
- A view-only reader cannot write after warming detail reads.
- Committed value changes appear immediately in detail and search projection.
- Permission downgrade removes the child from search, count and detail immediately;
  restoration makes it readable again.
- Removing asserted resource membership leaves an orphan annotation but no access.
- Removing a user's role immediately removes search/count/detail access even with
  the previously issued access token; fresh login has the same current result.
- Restoring the role and logging in restores the authorized result.
- Account deactivation refuses both new credential login and refresh.

## Authentication boundary: important distinction

The existing [authentication architecture](../../oldaplib/docs/authentication_architecture_roadmap.md)
explicitly keeps normal access-token validation stateless. An already issued
access token remains usable until expiry, normally 15 minutes, even after
account deactivation. This acceptance test reproduces that behavior. It is not
caused by Redis and this change does not introduce immediate token revocation.

Resource and role checks above concern the tested instance search/count/detail
queries. They do not imply that every authorization claim embedded in a JWT is
refreshed immediately, nor do they cover every administrative or media endpoint.
A different account-wide revocation policy requires its own architecture decision.

## Reproduction and limits

Run `tools/migration/probe_api_jena.py --cache-only --java <java> --jar <fuseki-jar>
--output <new-private-directory>` from the API repository's environment.
`redis-server` must be installed. This mode is separate from the full Fasnacht
import/profile modes. Evidence: `jena-cache-reads-results.json`.

The acceptance uses sequential and bounded concurrent requests, two synthetic
resources and actual Redis serialization. It does not claim production-scale
cache performance, exhaustive concurrent mutation correctness, browser behavior
or complete real-user migration parity. Application behavior and public API/library signatures are unchanged;
only acceptance tooling, retained evidence and documentation were added.


## Concurrent permission changes (2026-10-31)

The same `--cache-only` run now also starts four independent HTTP clients, two
using the reader identity and two the unrelated identity. Each owns its session
and reads search/count/detail twice per phase. Seven phases cover the warm
baseline, object-grant downgrade and user-role removal, and each confirmed
revocation/restoration. The reader's existing token is retained throughout.

All **26 focused HTTP checks** pass, including **168 concurrent-phase requests**.
Sixteen requests overlapped the object mutation window, and thirteen overlapped
the role mutation window. This verifies overlapping client request intervals;
it does not prove simultaneous execution inside the database. All 48 requests
in the two post-revocation phases hide the resource. Restored permissions return
the reader's result immediately; the outsider never receives it in any phase.
There were no unexpected HTTP errors. No application change was necessary.

Consistency is checked at the acknowledgment boundary: a request overlapping
an update may see the previous or new committed state. Separate requests started
after the successful mutation response must see the new access state. Separate
search/count/detail requests are not treated as a single database snapshot.
A barrier starts each phase together, and post-revocation workers are created
only after the writer's success response. The test asserts actual overlap and
fails rather than silently counting a sequential run as concurrent acceptance.

Evidence: `jena-cache-concurrency-results.json`. This is a bounded four-client
regression check, not a load-capacity or multi-process deployment benchmark.
