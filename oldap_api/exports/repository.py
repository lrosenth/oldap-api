"""Persistence boundary for project-neutral ZIP export jobs."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Protocol

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD

from .domain import ExportJob, ExportNotificationStatus, ExportState, ExportTask
from .manifest import ExportManifest
from .settings import ExportOperatingPolicy

EXPORT_GRAPH = URIRef("urn:oldap:export-jobs")
EXPORT_JOB_CLASS = URIRef("urn:oldap:ExportJob")
PAYLOAD = URIRef("urn:oldap:exportPayload")
OWNER = URIRef("urn:oldap:exportOwner")
STATE = URIRef("urn:oldap:exportState")
STATE_VERSION = URIRef("urn:oldap:exportStateVersion")
CREATED_AT = URIRef("urn:oldap:exportCreatedAt")
EXPORT_MANIFEST_CLASS = URIRef("urn:oldap:ExportManifest")
MANIFEST_PAYLOAD = URIRef("urn:oldap:exportManifestPayload")
MANIFEST_SHA256 = URIRef("urn:oldap:exportManifestSha256")
MANIFEST_FOR = URIRef("urn:oldap:exportManifestFor")
ACTIVE_CLAIM = URIRef("urn:oldap:exportActiveClaim")


class ExportNotFoundError(LookupError):
    """Raised when an export is absent or intentionally hidden from a caller."""


class ExportAlreadyExistsError(ValueError):
    """Raised when a repository would replace an existing export."""


class ExportRepositoryConflict(ValueError):
    """Raised when an optimistic repository write observes stale state."""


class ExportQuotaExceededError(ValueError):
    """Raised when an atomic job reservation exceeds deployment policy."""


class ExportJobRepository(Protocol):
    """Storage contract to be implemented atomically in the OLDAP job graph."""

    def create(self, job: ExportJob) -> None: ...

    def create_with_manifest(
        self,
        job: ExportJob,
        manifest: ExportManifest,
        *,
        operating_policy: ExportOperatingPolicy | None = None,
    ) -> None: ...

    def get(self, export_id: str) -> ExportJob: ...

    def get_manifest(self, export_id: str) -> ExportManifest: ...

    def save(self, job: ExportJob, *, expected_previous_version: int) -> None: ...

    def list_for_user(
        self, user_iri: str, *, state: ExportState | None = None
    ) -> tuple[ExportJob, ...]: ...

    def claim_next(
        self,
        *,
        worker_id: str,
        supported_tasks: tuple[ExportTask, ...],
        claim_id: str,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> ExportJob | None: ...

    def get_by_claim(self, claim_id: str) -> ExportJob: ...

    def renew_claim(self, current: ExportJob, renewed: ExportJob) -> None: ...

    def expire_next_ready(self, *, now: datetime) -> ExportJob | None: ...

    def next_notification_retry(
        self, *, now: datetime, retry_after: timedelta
    ) -> ExportJob | None: ...

    def update_notification(self, current: ExportJob, updated: ExportJob) -> None: ...

    def purge_expired_audits(self, *, now: datetime) -> int: ...

    def complete_cleanup(self, current: ExportJob, deleted: ExportJob) -> None: ...


class InMemoryExportJobRepository:
    """Deterministic Phase-0 repository used to prove persistence semantics."""

    def __init__(self) -> None:
        self._jobs: dict[str, ExportJob] = {}
        self._manifests: dict[str, ExportManifest] = {}
        self._lock = RLock()

    def create(self, job: ExportJob) -> None:
        """Insert one job without ever replacing an existing identifier."""

        with self._lock:
            if job.export_id in self._jobs:
                raise ExportAlreadyExistsError(job.export_id)
            self._jobs[job.export_id] = job

    def create_with_manifest(
        self,
        job: ExportJob,
        manifest: ExportManifest,
        *,
        operating_policy: ExportOperatingPolicy | None = None,
    ) -> None:
        """Atomically insert a job and its immutable bound manifest."""

        manifest.validate_for_job(job)
        with self._lock:
            if job.export_id in self._jobs or job.export_id in self._manifests:
                raise ExportAlreadyExistsError(job.export_id)
            if operating_policy is not None:
                _require_quota(tuple(self._jobs.values()), job, operating_policy)
            self._jobs[job.export_id] = job
            self._manifests[job.export_id] = manifest

    def get(self, export_id: str) -> ExportJob:
        """Return one immutable job or raise the privacy-neutral absence error."""

        with self._lock:
            try:
                return self._jobs[export_id]
            except KeyError as error:
                raise ExportNotFoundError(export_id) from error

    def get_manifest(self, export_id: str) -> ExportManifest:
        """Return one immutable manifest or the privacy-neutral absence error."""

        with self._lock:
            try:
                return self._manifests[export_id]
            except KeyError as error:
                raise ExportNotFoundError(export_id) from error

    def save(self, job: ExportJob, *, expected_previous_version: int) -> None:
        """Replace one job only after comparing its previously persisted version."""

        with self._lock:
            current = self._jobs.get(job.export_id)
            if current is None:
                raise ExportNotFoundError(job.export_id)
            if current.state_version != expected_previous_version:
                raise ExportRepositoryConflict(
                    f"Expected persisted version {expected_previous_version}, "
                    f"current version is {current.state_version}."
                )
            if job.state_version != expected_previous_version + 1:
                raise ExportRepositoryConflict(
                    "Saved export must advance stateVersion exactly once."
                )
            self._jobs[job.export_id] = job

    def list_for_user(
        self, user_iri: str, *, state: ExportState | None = None
    ) -> tuple[ExportJob, ...]:
        """Return caller-owned jobs newest first without cross-user leakage."""

        with self._lock:
            selected = [
                job
                for job in self._jobs.values()
                if job.requested_by_iri == user_iri
                and (state is None or job.state is state)
            ]
        return tuple(sorted(selected, key=lambda job: job.created_at, reverse=True))

    def claim_next(
        self,
        *,
        worker_id: str,
        supported_tasks: tuple[ExportTask, ...],
        claim_id: str,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> ExportJob | None:
        """Atomically lease the oldest eligible cleanup or build task."""

        with self._lock:
            candidate = _select_claim_candidate(
                tuple(self._jobs.values()), supported_tasks, claimed_at
            )
            if candidate is None:
                return None
            claimed = _attach_claim(
                candidate,
                _task_for_job(candidate, supported_tasks, claimed_at),
                claim_id,
                worker_id,
                claimed_at,
                lease_expires_at,
            )
            self._jobs[claimed.export_id] = claimed
            return claimed

    def get_by_claim(self, claim_id: str) -> ExportJob:
        """Return the job carrying one active claim identifier."""

        with self._lock:
            for job in self._jobs.values():
                if job.active_claim_id == claim_id:
                    return job
        raise ExportNotFoundError("Export claim not found.")

    def renew_claim(self, current: ExportJob, renewed: ExportJob) -> None:
        """Replace only the lease expiry without advancing stateVersion."""

        with self._lock:
            persisted = self._jobs.get(current.export_id)
            if persisted != current or not _is_lease_renewal(current, renewed):
                raise ExportRepositoryConflict("Export claim changed concurrently.")
            self._jobs[current.export_id] = renewed

    def expire_next_ready(self, *, now: datetime) -> ExportJob | None:
        """Atomically move the oldest elapsed READY job to EXPIRED."""

        with self._lock:
            candidate = _select_expired_ready(tuple(self._jobs.values()), now)
            if candidate is None:
                return None
            expired = candidate.transition(
                ExportState.EXPIRED,
                expected_state_version=candidate.state_version,
                now=now,
                cleanup_reason=ExportState.EXPIRED.value,
            )
            self._jobs[candidate.export_id] = expired
            return expired

    def next_notification_retry(
        self, *, now: datetime, retry_after: timedelta
    ) -> ExportJob | None:
        """Return the oldest due notification without mutating lifecycle state."""

        with self._lock:
            return _select_notification_retry(
                tuple(self._jobs.values()), now, retry_after
            )

    def update_notification(self, current: ExportJob, updated: ExportJob) -> None:
        """Persist only notification delivery evidence at the same version."""

        with self._lock:
            if self._jobs.get(
                current.export_id
            ) != current or not _is_notification_update(current, updated):
                raise ExportRepositoryConflict(
                    "Export notification changed concurrently."
                )
            self._jobs[current.export_id] = updated

    def purge_expired_audits(self, *, now: datetime) -> int:
        """Delete content-free DELETED job hulls after their audit deadline."""

        with self._lock:
            identifiers = [
                job.export_id
                for job in self._jobs.values()
                if _audit_is_expired(job, now)
            ]
            for identifier in identifiers:
                self._jobs.pop(identifier, None)
                self._manifests.pop(identifier, None)
            return len(identifiers)

    def complete_cleanup(self, current: ExportJob, deleted: ExportJob) -> None:
        """Atomically retain the audit job and remove its content manifest."""

        with self._lock:
            persisted = self._jobs.get(current.export_id)
            if (
                persisted != current
                or deleted.state_version != current.state_version + 1
            ):
                raise ExportRepositoryConflict("Export cleanup changed concurrently.")
            self._jobs[current.export_id] = deleted
            self._manifests.pop(current.export_id, None)


class TransactionalConnection(Protocol):
    """Subset of the OLDAP connection required by export persistence."""

    def query(self, query: str) -> Any: ...

    def transaction_start(self) -> None: ...

    def transaction_query(self, query: str) -> Any: ...

    def transaction_update(self, query: str) -> None: ...

    def transaction_commit(self) -> None: ...

    def transaction_abort(self) -> None: ...


class GraphDbExportJobRepository:
    """Persist canonical export jobs with indexed facts in one named graph.

    The complete internal JSON representation is authoritative. Indexed
    triples are intentionally limited to ownership, ordering, filtering, and
    optimistic locking. Every write validates and mutates within one GraphDB
    transaction.
    """

    def __init__(self, connection: TransactionalConnection) -> None:
        self._connection = connection

    def create(self, job: ExportJob) -> None:
        """Insert one new job atomically without replacing an existing UUID."""

        self._connection.transaction_start()
        try:
            if self._exists(job.export_id, transactional=True):
                raise ExportAlreadyExistsError(job.export_id)
            self._connection.transaction_update(self._insert(job))
            self._connection.transaction_commit()
        except Exception:
            self._connection.transaction_abort()
            raise

    def create_with_manifest(
        self,
        job: ExportJob,
        manifest: ExportManifest,
        *,
        operating_policy: ExportOperatingPolicy | None = None,
    ) -> None:
        """Publish one immutable job/manifest pair in a single transaction."""

        manifest.validate_for_job(job)
        self._connection.transaction_start()
        try:
            if self._exists(job.export_id, transactional=True) or self._manifest_exists(
                job.export_id, transactional=True
            ):
                raise ExportAlreadyExistsError(job.export_id)
            if operating_policy is not None:
                _require_quota(self._all(transactional=True), job, operating_policy)
            update = (
                f"INSERT DATA {{ GRAPH {EXPORT_GRAPH.n3()} {{ "
                f"{_job_triples(job)} {_manifest_triples(manifest)} }} }}"
            )
            self._connection.transaction_update(update)
            self._connection.transaction_commit()
        except Exception:
            self._connection.transaction_abort()
            raise

    def get(self, export_id: str) -> ExportJob:
        """Read one complete job by UUID."""

        rows = _bindings(self._connection.query(self._select_one(export_id)))
        if not rows:
            raise ExportNotFoundError(export_id)
        return ExportJob.from_dict(json.loads(rows[0]["payload"]["value"]))

    def get_manifest(self, export_id: str) -> ExportManifest:
        """Read and digest-verify one immutable manifest by export UUID."""

        query = f"""
SELECT ?payload ?sha256
WHERE {{ GRAPH {EXPORT_GRAPH.n3()} {{
  {_manifest_iri(export_id).n3()} {MANIFEST_PAYLOAD.n3()} ?payload ;
       {MANIFEST_SHA256.n3()} ?sha256 ;
       {MANIFEST_FOR.n3()} {_job_iri(export_id).n3()} .
}} }}
LIMIT 1
"""
        rows = _bindings(self._connection.query(query))
        if not rows:
            raise ExportNotFoundError(export_id)
        manifest = ExportManifest.from_dict(json.loads(rows[0]["payload"]["value"]))
        if manifest.sha256 != rows[0]["sha256"]["value"]:
            raise ExportRepositoryConflict("Persisted export manifest digest mismatch.")
        return manifest

    def save(self, job: ExportJob, *, expected_previous_version: int) -> None:
        """Replace one job after an atomic optimistic-version comparison."""

        self._connection.transaction_start()
        try:
            current = self._get_transactional(job.export_id)
            if current.state_version != expected_previous_version:
                raise ExportRepositoryConflict(
                    f"Expected persisted version {expected_previous_version}, "
                    f"current version is {current.state_version}."
                )
            if job.state_version != expected_previous_version + 1:
                raise ExportRepositoryConflict(
                    "Saved export must advance stateVersion exactly once."
                )
            self._connection.transaction_update(self._replace(current, job))
            self._connection.transaction_commit()
        except Exception:
            self._connection.transaction_abort()
            raise

    def list_for_user(
        self, user_iri: str, *, state: ExportState | None = None
    ) -> tuple[ExportJob, ...]:
        """List caller-owned jobs newest first, optionally filtered by state."""

        state_triple = (
            f"?job {STATE.n3()} {Literal(state.value).n3()} ." if state else ""
        )
        query = f"""
SELECT ?payload ?created
WHERE {{
  GRAPH {EXPORT_GRAPH.n3()} {{
    ?job {RDF.type.n3()} {EXPORT_JOB_CLASS.n3()} ;
         {OWNER.n3()} {URIRef(user_iri).n3()} ;
         {PAYLOAD.n3()} ?payload ;
         {CREATED_AT.n3()} ?created .
    {state_triple}
  }}
}}
ORDER BY DESC(?created) DESC(?job)
"""
        return tuple(
            ExportJob.from_dict(json.loads(row["payload"]["value"]))
            for row in _bindings(self._connection.query(query))
        )

    def claim_next(
        self,
        *,
        worker_id: str,
        supported_tasks: tuple[ExportTask, ...],
        claim_id: str,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> ExportJob | None:
        """Atomically lease the oldest eligible cleanup or build task."""

        self._connection.transaction_start()
        try:
            jobs = self._all(transactional=True)
            candidate = _select_claim_candidate(jobs, supported_tasks, claimed_at)
            if candidate is None:
                self._connection.transaction_commit()
                return None
            claimed = _attach_claim(
                candidate,
                _task_for_job(candidate, supported_tasks, claimed_at),
                claim_id,
                worker_id,
                claimed_at,
                lease_expires_at,
            )
            self._connection.transaction_update(self._replace(candidate, claimed))
            self._connection.transaction_commit()
            return claimed
        except Exception:
            self._connection.transaction_abort()
            raise

    def get_by_claim(self, claim_id: str) -> ExportJob:
        """Read the job carrying one active worker claim."""

        query = f"""
SELECT ?payload
WHERE {{ GRAPH {EXPORT_GRAPH.n3()} {{
  ?job {ACTIVE_CLAIM.n3()} {Literal(claim_id).n3()} ; {PAYLOAD.n3()} ?payload .
}} }}
LIMIT 1
"""
        rows = _bindings(self._connection.query(query))
        if not rows:
            raise ExportNotFoundError("Export claim not found.")
        return ExportJob.from_dict(json.loads(rows[0]["payload"]["value"]))

    def renew_claim(self, current: ExportJob, renewed: ExportJob) -> None:
        """Renew a lease atomically without changing lifecycle stateVersion."""

        if not _is_lease_renewal(current, renewed):
            raise ExportRepositoryConflict("Only the claim lease may be renewed.")
        self._connection.transaction_start()
        try:
            persisted = self._get_transactional(current.export_id)
            if persisted != current:
                raise ExportRepositoryConflict("Export claim changed concurrently.")
            self._connection.transaction_update(self._replace(current, renewed))
            self._connection.transaction_commit()
        except Exception:
            self._connection.transaction_abort()
            raise

    def expire_next_ready(self, *, now: datetime) -> ExportJob | None:
        """Atomically move the oldest elapsed READY job to EXPIRED."""

        self._connection.transaction_start()
        try:
            candidate = _select_expired_ready(self._all(transactional=True), now)
            if candidate is None:
                self._connection.transaction_commit()
                return None
            expired = candidate.transition(
                ExportState.EXPIRED,
                expected_state_version=candidate.state_version,
                now=now,
                cleanup_reason=ExportState.EXPIRED.value,
            )
            self._connection.transaction_update(self._replace(candidate, expired))
            self._connection.transaction_commit()
            return expired
        except Exception:
            self._connection.transaction_abort()
            raise

    def next_notification_retry(
        self, *, now: datetime, retry_after: timedelta
    ) -> ExportJob | None:
        """Return the oldest due notification retry candidate."""

        return _select_notification_retry(
            self._all(transactional=False), now, retry_after
        )

    def update_notification(self, current: ExportJob, updated: ExportJob) -> None:
        """Persist only notification delivery evidence at the same version."""

        if not _is_notification_update(current, updated):
            raise ExportRepositoryConflict("Only notification evidence may change.")
        self._connection.transaction_start()
        try:
            persisted = self._get_transactional(current.export_id)
            if persisted != current:
                raise ExportRepositoryConflict(
                    "Export notification changed concurrently."
                )
            self._connection.transaction_update(self._replace(current, updated))
            self._connection.transaction_commit()
        except Exception:
            self._connection.transaction_abort()
            raise

    def purge_expired_audits(self, *, now: datetime) -> int:
        """Delete content-free DELETED job hulls after their audit deadline."""

        self._connection.transaction_start()
        try:
            due = tuple(
                job
                for job in self._all(transactional=True)
                if _audit_is_expired(job, now)
            )
            for job in due:
                job_iri = _job_iri(job.export_id).n3()
                manifest_iri = _manifest_iri(job.export_id).n3()
                self._connection.transaction_update(
                    f"DELETE WHERE {{ GRAPH {EXPORT_GRAPH.n3()} {{ {job_iri} ?p ?o . }} }}"
                )
                self._connection.transaction_update(
                    f"DELETE WHERE {{ GRAPH {EXPORT_GRAPH.n3()} {{ {manifest_iri} ?p ?o . }} }}"
                )
            self._connection.transaction_commit()
            return len(due)
        except Exception:
            self._connection.transaction_abort()
            raise

    def complete_cleanup(self, current: ExportJob, deleted: ExportJob) -> None:
        """Atomically persist deletion proof and purge the immutable manifest."""

        if deleted.state_version != current.state_version + 1:
            raise ExportRepositoryConflict("Cleanup must advance stateVersion once.")
        self._connection.transaction_start()
        try:
            persisted = self._get_transactional(current.export_id)
            if persisted != current:
                raise ExportRepositoryConflict("Export cleanup changed concurrently.")
            self._connection.transaction_update(self._replace(current, deleted))
            manifest = _manifest_iri(current.export_id).n3()
            self._connection.transaction_update(
                f"DELETE WHERE {{ GRAPH {EXPORT_GRAPH.n3()} {{ {manifest} ?p ?o . }} }}"
            )
            self._connection.transaction_commit()
        except Exception:
            self._connection.transaction_abort()
            raise

    def _get_transactional(self, export_id: str) -> ExportJob:
        rows = _bindings(
            self._connection.transaction_query(self._select_one(export_id))
        )
        if not rows:
            raise ExportNotFoundError(export_id)
        return ExportJob.from_dict(json.loads(rows[0]["payload"]["value"]))

    def _all(self, *, transactional: bool) -> tuple[ExportJob, ...]:
        query = f"""
SELECT ?payload ?created
WHERE {{ GRAPH {EXPORT_GRAPH.n3()} {{
  ?job {RDF.type.n3()} {EXPORT_JOB_CLASS.n3()} ;
       {PAYLOAD.n3()} ?payload ; {CREATED_AT.n3()} ?created .
}} }}
ORDER BY ?created ?job
"""
        result = (
            self._connection.transaction_query(query)
            if transactional
            else self._connection.query(query)
        )
        return tuple(
            ExportJob.from_dict(json.loads(row["payload"]["value"]))
            for row in _bindings(result)
        )

    def _exists(self, export_id: str, *, transactional: bool) -> bool:
        query = f"""
ASK {{ GRAPH {EXPORT_GRAPH.n3()} {{
  {_job_iri(export_id).n3()} {RDF.type.n3()} {EXPORT_JOB_CLASS.n3()}
}} }}
"""
        result = (
            self._connection.transaction_query(query)
            if transactional
            else self._connection.query(query)
        )
        return bool(result.get("boolean"))

    def _manifest_exists(self, export_id: str, *, transactional: bool) -> bool:
        query = f"""
ASK {{ GRAPH {EXPORT_GRAPH.n3()} {{
  {_manifest_iri(export_id).n3()} {RDF.type.n3()} {EXPORT_MANIFEST_CLASS.n3()}
}} }}
"""
        result = (
            self._connection.transaction_query(query)
            if transactional
            else self._connection.query(query)
        )
        return bool(result.get("boolean"))

    @staticmethod
    def _select_one(export_id: str) -> str:
        return f"""
SELECT ?payload
WHERE {{ GRAPH {EXPORT_GRAPH.n3()} {{
  {_job_iri(export_id).n3()} {PAYLOAD.n3()} ?payload .
}} }}
LIMIT 1
"""

    @staticmethod
    def _insert(job: ExportJob) -> str:
        return f"INSERT DATA {{ GRAPH {EXPORT_GRAPH.n3()} {{ {_job_triples(job)} }} }}"

    @staticmethod
    def _replace(current: ExportJob, updated: ExportJob) -> str:
        iri = _job_iri(current.export_id).n3()
        return f"""
DELETE {{ GRAPH {EXPORT_GRAPH.n3()} {{ {iri} ?property ?value . }} }}
INSERT {{ GRAPH {EXPORT_GRAPH.n3()} {{ {_job_triples(updated)} }} }}
WHERE  {{ GRAPH {EXPORT_GRAPH.n3()} {{
  {iri} {STATE_VERSION.n3()} {Literal(current.state_version).n3()} ;
        ?property ?value .
}} }}
"""


def _job_iri(export_id: str) -> URIRef:
    return URIRef(f"urn:oldap:export:{export_id}")


def _manifest_iri(export_id: str) -> URIRef:
    return URIRef(f"urn:oldap:export-manifest:{export_id}")


def _job_triples(job: ExportJob) -> str:
    payload = json.dumps(
        job.to_persisted_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    active_claim = (
        f"{_job_iri(job.export_id).n3()} {ACTIVE_CLAIM.n3()} "
        f"{Literal(job.active_claim_id).n3()} ."
        if job.active_claim_id
        else ""
    )
    return f"""
{_job_iri(job.export_id).n3()} {RDF.type.n3()} {EXPORT_JOB_CLASS.n3()} ;
  {PAYLOAD.n3()} {Literal(payload).n3()} ;
  {OWNER.n3()} {URIRef(job.requested_by_iri).n3()} ;
  {STATE.n3()} {Literal(job.state.value).n3()} ;
  {STATE_VERSION.n3()} {Literal(job.state_version, datatype=XSD.integer).n3()} ;
  {CREATED_AT.n3()} {Literal(job.created_at, datatype=XSD.dateTime).n3()} .
{active_claim}
"""


def _manifest_triples(manifest: ExportManifest) -> str:
    payload = manifest.canonical_json.decode("utf-8")
    return f"""
{_manifest_iri(manifest.export_id).n3()} {RDF.type.n3()} {EXPORT_MANIFEST_CLASS.n3()} ;
  {MANIFEST_PAYLOAD.n3()} {Literal(payload).n3()} ;
  {MANIFEST_SHA256.n3()} {Literal(manifest.sha256).n3()} ;
  {MANIFEST_FOR.n3()} {_job_iri(manifest.export_id).n3()} .
"""


def _bindings(result: Any) -> list[dict[str, Any]]:
    return list(result.get("results", {}).get("bindings", []))


def _require_quota(
    jobs: tuple[ExportJob, ...],
    candidate: ExportJob,
    policy: ExportOperatingPolicy,
) -> None:
    """Reserve active-job and retained-byte capacity in the create transaction."""

    active_states = {ExportState.QUEUED, ExportState.BUILDING}
    retained = tuple(job for job in jobs if job.state is not ExportState.DELETED)
    active = tuple(job for job in retained if job.state in active_states)
    owner_active = tuple(
        job for job in active if job.requested_by_iri == candidate.requested_by_iri
    )
    owner_retained = tuple(
        job for job in retained if job.requested_by_iri == candidate.requested_by_iri
    )
    if len(owner_active) >= policy.max_active_jobs_per_user:
        raise ExportQuotaExceededError("The user's active export-job quota is full.")
    if len(active) >= policy.max_active_jobs_total:
        raise ExportQuotaExceededError("The system active export-job quota is full.")
    if (
        sum(job.estimated_source_bytes for job in owner_retained)
        + candidate.estimated_source_bytes
        > policy.max_reserved_bytes_per_user
    ):
        raise ExportQuotaExceededError("The user's retained export-byte quota is full.")
    if (
        sum(job.estimated_source_bytes for job in retained)
        + candidate.estimated_source_bytes
        > policy.max_reserved_bytes_total
    ):
        raise ExportQuotaExceededError("The system retained export-byte quota is full.")


def _select_claim_candidate(
    jobs: tuple[ExportJob, ...],
    supported_tasks: tuple[ExportTask, ...],
    now: datetime,
) -> ExportJob | None:
    """Select cleanup before build, then preserve oldest-job ordering."""

    ordered = sorted(jobs, key=lambda job: (job.created_at, job.export_id))
    for task in (ExportTask.CLEANUP, ExportTask.BUILD):
        if task not in supported_tasks:
            continue
        for job in ordered:
            if _job_is_claimable(job, task, now):
                return job
    return None


def _select_expired_ready(
    jobs: tuple[ExportJob, ...], now: datetime
) -> ExportJob | None:
    """Return the oldest unclaimed READY job whose retention elapsed."""

    return next(
        (
            job
            for job in sorted(jobs, key=lambda item: (item.created_at, item.export_id))
            if job.state is ExportState.READY
            and job.expires_at is not None
            and job.expires_at <= now
            and job.active_claim_id is None
        ),
        None,
    )


def _select_notification_retry(
    jobs: tuple[ExportJob, ...], now: datetime, retry_after: timedelta
) -> ExportJob | None:
    """Return at most one bounded, backed-off notification candidate."""

    return next(
        (
            job
            for job in sorted(jobs, key=lambda item: (item.created_at, item.export_id))
            if job.notification_status
            in {ExportNotificationStatus.PENDING, ExportNotificationStatus.FAILED}
            and (
                job.notification_for_state is ExportState.FAILED
                or job.state is ExportState.READY
            )
            and job.notification_attempts < 3
            and (
                job.notification_last_attempt_at is None
                or job.notification_last_attempt_at + retry_after <= now
            )
        ),
        None,
    )


def _audit_is_expired(job: ExportJob, now: datetime) -> bool:
    return (
        job.state is ExportState.DELETED
        and job.audit_delete_at is not None
        and job.audit_delete_at <= now
    )


def _task_for_job(
    job: ExportJob,
    supported_tasks: tuple[ExportTask, ...],
    now: datetime,
) -> ExportTask:
    for task in (ExportTask.CLEANUP, ExportTask.BUILD):
        if task in supported_tasks and _job_is_claimable(job, task, now):
            return task
    raise RuntimeError("Export claim candidate has no eligible task.")


def _job_is_claimable(job: ExportJob, task: ExportTask, now: datetime) -> bool:
    active = (
        job.active_claim_id is not None
        and job.active_claim_lease_expires_at is not None
        and job.active_claim_lease_expires_at > now
    )
    if active:
        return False
    if task is ExportTask.BUILD:
        return job.state in {ExportState.QUEUED, ExportState.BUILDING}
    return job.state in {
        ExportState.FAILED,
        ExportState.CANCELLED,
        ExportState.EXPIRED,
        ExportState.DELETING,
    }


def _attach_claim(
    job: ExportJob,
    task: ExportTask,
    claim_id: str,
    worker_id: str,
    claimed_at: datetime,
    lease_expires_at: datetime,
) -> ExportJob:
    state = ExportState.BUILDING if task is ExportTask.BUILD else ExportState.DELETING
    cleanup_reason = job.cleanup_reason
    if task is ExportTask.CLEANUP and cleanup_reason is None:
        cleanup_reason = job.state.value
    return replace(
        job,
        state=state,
        state_version=job.state_version + 1,
        updated_at=claimed_at,
        active_claim_id=claim_id,
        active_claim_task=task,
        active_claim_worker_id=worker_id,
        active_claimed_at=claimed_at,
        active_claim_lease_expires_at=lease_expires_at,
        active_claim_lease_seconds=int((lease_expires_at - claimed_at).total_seconds()),
        cleanup_reason=cleanup_reason,
    )


def _is_lease_renewal(current: ExportJob, renewed: ExportJob) -> bool:
    """Return whether two jobs differ only by a later lease expiry."""

    if (
        current.active_claim_id is None
        or renewed.active_claim_lease_expires_at is None
        or current.active_claim_lease_expires_at is None
        or renewed.active_claim_lease_expires_at
        <= current.active_claim_lease_expires_at
    ):
        return False
    return (
        replace(
            renewed,
            active_claim_lease_expires_at=current.active_claim_lease_expires_at,
        )
        == current
    )


def _is_notification_update(current: ExportJob, updated: ExportJob) -> bool:
    """Return whether only same-version notification evidence changed."""

    if (
        current.export_id != updated.export_id
        or current.state_version != updated.state_version
    ):
        return False
    fields = (
        "notification_status",
        "notification_attempts",
        "notification_sent_at",
        "notification_last_attempt_at",
        "notification_last_error",
    )
    return (
        replace(updated, **{field: getattr(current, field) for field in fields})
        == current
    )
