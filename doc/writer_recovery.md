# Writer recovery application service (WR-02)

`oldap_api.writer_recovery.WriterRecoveryService` is the reusable authorization
boundary for the later WR-03 HTTP adapters. It deliberately registers no route and
changes no existing response, Capture transport or ordinary archive capability.

Configuration is opt-in: `OLDAP_WRITER_DOMAIN`,
`OLDAP_WRITER_RECOVERY_REDIS_URL` (the separate recovery-api ACL identity),
`OLDAP_WRITER_RECOVERY_ROLE_IRI` (absolute ordinary OLDAP role), and
`OLDAP_WRITER_RECOVERY_INVENTORY_SHA256` (reviewed offline runtime inventory digest).
No privilege is inherited from archive roles or ADMIN_OLDAP. Every operation, status
read and exact retry queries current active-user role membership directly from
`oldap:admin`, bypassing cached JWT role information. An unavailable permission
query denies the action. Configure/grant the role through oldap-app only for
explicitly selected deployment operators; no users were assigned by this change.

Use an authenticated Connection, then call `status`, `operation`, `begin` or
`finish`. Actor identity always comes from that Connection. `begin` requires an
operation UUID, exact inspected revision and a reason; `finish` accepts only the
operation UUID. Evidence/termination flags, runtime targets, transaction URLs and
shell commands must never become HTTP inputs. Restrict journal details to operators
and translate internal exceptions to a no-store sanitized error envelope in WR-03.
After a lost response read/retry the SAME operation UUID; completed results do not
release successor gates. The service creates no database mutation transaction and
can operate while ordinary resource writes are blocked. Authentication still needs
GraphDB, so the independent offline tool remains available while APIs/GraphDB stop.

See oldaplib `docs/writer_recovery.md` and oldap-setup `docs/writer-recovery.md` for
the two-phase operator proof, ACL boundary, controller-crash procedure and target
acceptance limits. Native MacBook control and actual target activation remain
unperformed; no unrestricted Docker/SSH access belongs in the web service.

## WR-03 HTTP adapters

The separate `views/writer_recovery_views.py` blueprint is now registered by the API
factory. Additive bearer-authenticated routes under `/admin/writer-recovery` expose
capabilities, status, POST operations, GET operations/{identifier}, and POST
operations/{identifier}/finish. See `API-def/oldap-api.yaml` for the closed schemas.
Discovery may return disabled or unprivileged without exposing operational facts;
all other routes freshly authorize the active operational role.

POST begin accepts only operationId (canonical UUID), expectedRevision (64-hex) and
reason (10–2000 trimmed characters). POST finish accepts an empty JSON object. The
8-KiB request limit is enforced before parsing. Responses are no-store and project
only state/revision/start time or operation ID/reason/request/completion time and
advisory canFinish. No raw owner, runtime, evidence or transaction data is exposed.
Readiness and authoritative release share the proof-binding predicate; an active
controller always prevents readiness. The Redis pool closes after each request.

`Connection.query(timeout=(5, 10))` bounds the fresh role query without changing the
default for other clients. 400 denotes malformed input, 403 missing privilege, 409
blocked recovery, 413 oversized body, and 503 disabled/unavailable/unknown outcome.
Missing/invalid authentication retains the uniform 401 contract. A failed durability
acknowledgement maps to RESULT_UNKNOWN rather than a definite refusal. Read/retry the
same operation ID; do not infer that a 503 means no change occurred. Internal errors
are sanitized and never echo connection secrets.

Both administration clients use these endpoints. Native runtime control and actual
activation remain WR-04 work; no existing Capture or archive transport was changed.
Cross-project scope and the operator's independent evidence path remain unchanged.


## WR-04 local activation

The shared MacBook API is now launchd-supervised and recovery is enabled for the
explicitly authorized rosenth operator. Real API/Redis ACL and both live browser
checks pass; the local CORS allowlist includes SALSAH on localhost:5175. Source
changes require a controlled API restart because the development reloader is
disabled. Capture contracts are unchanged. See FasnachtsPage `docs/wr-04/README.md`
for native control, backups/restore, acceptance evidence and production limits.
