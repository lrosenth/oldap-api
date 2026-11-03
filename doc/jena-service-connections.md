# API-owned Jena service connections

Export, import and mobile-media handlers authenticate a dedicated OLDAP service
account after checking the worker's purpose-specific JWT. Under GraphDB these
connections retain `issue_access_token=False`. Under Jena they request an access
token because the private HTTP transport and identity callback require it.
The API already holds the signing key; the token remains inside the API. Media
workers receive neither that key nor a general-purpose access token.

This is an explicit API-owned boundary, not a change to oldaplib's tokenless
connection contract. Service users, roles and passwords are unchanged. Regression
coverage exercises all four service constructors with both backend selections.

Deployment must route established `/internal/export-claims`, `/internal/exports`,
import and mobile-service endpoints to their existing JWT guards. Only the Jena
callback namespace `/internal/jena/*` is proxy-blocked. Native verification must
include a real worker claim and completed artifact, not just frontend status reads.


Import 503 diagnostics record the sanitized request ID, endpoint, exception types
and bounded stack/cause locations. Exception messages, source lines, locals and
request contents are excluded because they may contain tokens or RDF payloads.
Match the response requestId to `import_failure` in the API server log. A BEGIN
conflict can be distinguished from UPDATE/COMMIT uncertainty by its stack location;
never retry an uncertain write simply because the public response is 503.

The current ingestion worker stops its claim heartbeat when result publication
fails. Polling resumes after ten seconds, but no claim is eligible until the old
five-minute lease expires. The retained validation result avoids re-extraction.
Changing this recovery policy requires exact-event retry and uncertain-commit
coverage; it is not part of the diagnostic change.


The subsequent RC4 library change adds up to four retries only when BEGIN receives
an explicit HTTP 409 refusal (50/100/200/400 ms pauses, fresh journaled identifiers).
No public API change is required. Persistent contention still fails, and the worker
lease policy remains unchanged. Network loss, other HTTP failures and UPDATE/COMMIT
are not automatically replayed. This prevents brief writer collisions from
immediately turning into a worker lease wait without concealing uncertain writes.
