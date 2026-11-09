# Coordinated archive adoption writes on Jena

## Behavior

Archive adoption keeps its existing public HTTP and library contracts. The
normal policy-file loader, permission checks, durable writer coordination,
resource transactions, structural audit and actor-scoped receipt are exercised
together. Publication-specific policy is not required for structure adoption.

Two remaining GraphDB default-graph assumptions are removed for Jena:

- Preflight and ordinary archive-unit writes share a small archive-level query
  builder. It selects project/shared/base ontology graphs explicitly.
- Private-folder sibling-name checks select those schema graphs plus the named
  project data graph, including exact asserted folder types and subclasses.

Grant propagation additionally requires an asserted role membership on each
source folder. Revision snapshots intentionally retain orphan annotations, but
those must not become active permissions on a new unit. This correctness fix
applies to both backends; role caps, ancestor propagation and the optional
project creation-grant rule remain unchanged. Offline fixtures now include the
asserted membership rows that real snapshot queries return.

GraphDB retains its configured default dataset. No transaction buffering, new
public parameters or alternative audit/receipt mechanism is introduced.

## Owned acceptance

`tools/migration/check_archive_writes.py` runs after the prior read acceptance.
It starts its own socket-only Redis with `appendonly=yes`, `appendfsync=always`
and `maxmemory-policy=noeviction`. The existing gate checks the actual settings
and obtains WAITAOF acknowledgements. Its AOF and log stay in the owned probe
output directory. The process and socket are closed when the stage ends; the
user's existing Redis is never selected or reconfigured.

The stage sets a real server-owned archive policy file. Shared-model StagingArea
and folder instances are created through the real library under that policy and
gate. An ordinary writer receives ADMIN_CREATE through the normal API and still
needs the configured structure role and per-object data rights. Proposal,
preflight, apply and retry use real HTTP endpoints with the writer's token.

A rollback test invokes the same adoption service inside an enclosing resource
transaction, then deliberately raises after the units, mappings, structural audit
and receipt have been written. It verifies that all disappear or revert after
abort and that durable ownership is released. A confirmed aborted request can
then be submitted successfully through HTTP using the same operation ID.

The stage also checks actual persisted parent links, source mappings and RDF 1.2
writer grants, prevents revival of a synthetic orphaned source grant, rejects
stale apply requests and verifies structure-only mode: create units and retain
provenance without changing folder mappings or emitting folder-update audit.

As in earlier stages, object-cache Redis I/O is suppressed. This test uses real
Redis for coordination; it does not establish production cache behavior, crash
recovery after an ambiguous commit, multi-process throughput or failover safety.
Earlier crash-recovery probes remain separate evidence. All public API/library
signatures are unchanged.

## Results and next gates

The retained `jena-archive-writes-results.json` records 132 passing owned checks
(115 previous plus 17 coordinated-write checks). Targeted offline regressions
pass 106 library tests plus 24 subtests and 11 API tests plus 13 subtests.
The owned Redis process exits and its AOF/log remain available with the results.

Remaining gates include complete inventory/media hydration and specialized media
queries, raw project transfer/export jobs, real object-cache acceptance, and
normal-adapter recovery after process failure or an uncertain transaction outcome.
This run proves confirmed commit/abort behavior with durable coordination, not
recovery from every failure mode or readiness for production deployment.
