# Reviewed archive structure API (AS-04)

Three additive authenticated endpoints delegate to the project-neutral
`ArchiveAdoption` library service:

| Method/path | Body | Result |
| --- | --- | --- |
| POST `/archive/{project}/structure/proposal` | `ProposalRequest` | `ProposalResponse` |
| POST `/archive/{project}/structure/preflight` | `PreflightRequest` | `PreflightResponse` |
| POST `/archive/{project}/structure/apply` | `ApplyRequest` + UUID `Idempotency-Key` header | `ApplyResponse` |
| GET `/archive/{project}/structure/operations/{operationId}` | none | committed apply or reference-move result |

The authoritative frozen shapes are in `archive_structure_v1.schema.json`.
OpenAPI documents the bindings; JSON Schema additionally enforces language-key
patterns and closed target/action alternatives. Every response uses `no-store`.
New domain errors use `{code,message,requestId}`; authentication keeps the existing
401 `{message}` envelope. Legacy YAML, generic resource and Capture request/result
shapes are unchanged. No CaptureApp source change is needed for these endpoints.

Clients select a source folder, edit `suggestedPlan`, preflight that exact plan,
show its counts, and submit the plan with its review digest and `confirm: true`.
Keep one UUID for retries of the same logical apply. A new edited plan needs a new
UUID. Preserve the original request until its receipt is known. Apply is atomic;
never split a plan automatically. A missing receipt does not authorize a fresh
mutation. GET is owner-scoped and rechecks visibility; deleted/inaccessible
resources prevent replay disclosure. A UUID used for both distinct command types
makes GET ambiguous (409); replay the original endpoint instead.

Existing mappings are reused; existing archive names, levels, parents and grants
are never changed by adoption. Mapping-only plans use `newUnits: []`. Clear and
skip have no target; omitted source folders remain unchanged. Unavailable mappings
must remain unchanged. New grouping nodes may combine several source folders.
Rights for new nodes derive from those folders, not all configured structure roles;
see oldaplib `docs/reviewed_archive_adoption.md` for the precise caps and invariants.

Expected errors: 400 invalid request/hierarchy, 403 insufficient role/rights,
404 unavailable resource/receipt, 409 STALE_REVIEW or IDEMPOTENCY_CONFLICT,
413 TOO_LARGE, 503 unavailable coordination/configuration. A stale review requires
fresh proposal/preflight as appropriate. Limits: 2,000,000 body bytes, 5,000 source
folders, 500 combined new-unit and set/clear actions. Preflight is stateless, with
no timeout expiry, but relevant changes invalidate its digest.

Use matching library/API source versions and their declared dependencies. All
writers must share the same enabled policy and durable persistent gate settings.
No runtime policy, ontology, ACL or production deployment is changed by AS-04.
The FasnachtsPage admin tool and SALSAH integration follow in AS-06/AS-07.
