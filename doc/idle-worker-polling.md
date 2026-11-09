# Read-only idle worker polling

Import claims, export claims/expiry/audit purge, and mobile lifecycle claims now
read eligibility before starting a transaction. An empty queue does not reserve
a Jena transaction ID or create a commit receipt. Positive results are only hints:
all selection/expiry checks repeat under the existing transaction, preserving
atomic claims and concurrent-worker correctness. A job arriving just after an
empty precheck is picked up by the next normal poll.

The optimization applies equally to GraphDB and Jena. It changes no public API,
function signature, worker poll interval, lease, authorization or validation rule.
The required `query` method is included in the internal lifecycle connection
protocol. Real writes retain the original transaction and recovery behavior.

Regression coverage is in `oldap_api/test/test_idle_polling.py`, together with the
existing import/export/lifecycle repository and service tests. Native TDB
maintenance is described in sibling oldaplib's `docs/migration/jena-compaction.md`.
These source changes still require an updated API image before home or production
can benefit; the existing running image has not been modified in place.
