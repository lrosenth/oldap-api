"""Persistence contracts and GraphDB implementation for import jobs."""

from __future__ import annotations

import json
import os
import unicodedata
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Protocol

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD

from .authorization import (
    ImportPermissionDeniedError,
    ImportTargetNotFoundError,
    resolve_project_data_graph_iri,
)
from .commit import ImportCommit, ImportCommitConflict
from .domain import ImportJob, ImportState, ImportTask, ImportVersionConflict

IMPORT_GRAPH = URIRef("urn:oldap:import-jobs")
IMPORT_JOB_CLASS = URIRef("urn:oldap:ImportJob")
PAYLOAD = URIRef("urn:oldap:importPayload")
OWNER = URIRef("urn:oldap:importOwner")
STAGING_AREA = URIRef("urn:oldap:importStagingArea")
STATE_VERSION = URIRef("urn:oldap:importStateVersion")
QUOTA_RESERVED = URIRef("urn:oldap:importQuotaReservedBytes")
CREATED_AT = URIRef("urn:oldap:importCreatedAt")
ACTIVE_CLAIM = URIRef("urn:oldap:importActiveClaim")


class ImportNotFoundError(LookupError):
    """Raised when an import ID has no durable job record."""

    code = "IMPORT_NOT_FOUND"


class ImportQuotaExceededError(ValueError):
    """Raised when an atomic reservation would exceed the staging-area quota."""

    code = "IMPORT_QUOTA_EXCEEDED"


class ImportJobRepository(Protocol):
    """Atomic persistence boundary used by the import application service."""

    def create(self, job: ImportJob, *, quota_limit_bytes: int) -> None: ...

    def get(self, import_id: str) -> ImportJob: ...

    def list_for_owner(self, owner_iri: str) -> list[ImportJob]: ...

    def replace(
        self,
        job: ImportJob,
        *,
        expected_state_version: int,
        quota_limit_bytes: int | None = None,
    ) -> None: ...

    def claim_next(
        self,
        *,
        worker_id: str,
        supported_tasks: tuple[ImportTask, ...],
        claim_id: str,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> ImportJob | None: ...

    def get_by_claim(self, claim_id: str) -> ImportJob: ...

    def next_notification_retry(
        self, *, now: datetime, retry_after: timedelta
    ) -> ImportJob | None: ...

    def commit_import(
        self, current: ImportJob, updated: ImportJob, commit: ImportCommit
    ) -> None: ...


class InMemoryImportJobRepository:
    """Thread-safe reference repository used by focused domain/API tests."""

    def __init__(self) -> None:
        self._jobs: dict[str, ImportJob] = {}
        self._lock = RLock()
        self._resource_iris: set[str] = set()
        self._asset_ids: set[str] = set()

    def create(self, job: ImportJob, *, quota_limit_bytes: int) -> None:
        with self._lock:
            if job.import_id in self._jobs:
                raise ImportVersionConflict("Import ID already exists.")
            self._check_quota(job, quota_limit_bytes)
            self._jobs[job.import_id] = job

    def get(self, import_id: str) -> ImportJob:
        with self._lock:
            try:
                return self._jobs[import_id]
            except KeyError as error:
                raise ImportNotFoundError("Import job not found.") from error

    def list_for_owner(self, owner_iri: str) -> list[ImportJob]:
        with self._lock:
            return sorted(
                (
                    job
                    for job in self._jobs.values()
                    if job.requested_by_iri == owner_iri
                ),
                key=lambda job: (job.created_at, job.import_id),
                reverse=True,
            )

    def replace(
        self,
        job: ImportJob,
        *,
        expected_state_version: int,
        quota_limit_bytes: int | None = None,
    ) -> None:
        with self._lock:
            current = self.get(job.import_id)
            if current.state_version != expected_state_version:
                raise ImportVersionConflict("Import job changed concurrently.")
            if quota_limit_bytes is not None:
                self._check_quota(job, quota_limit_bytes, excluding=job.import_id)
            self._jobs[job.import_id] = job

    def claim_next(
        self,
        *,
        worker_id: str,
        supported_tasks: tuple[ImportTask, ...],
        claim_id: str,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> ImportJob | None:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_at)
            candidate = _select_claim_candidate(jobs, supported_tasks, claimed_at)
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
            self._jobs[claimed.import_id] = claimed
            return claimed

    def get_by_claim(self, claim_id: str) -> ImportJob:
        with self._lock:
            for job in self._jobs.values():
                if job.active_claim_id == claim_id:
                    return job
        raise ImportNotFoundError("Import claim not found.")

    def next_notification_retry(
        self, *, now: datetime, retry_after: timedelta
    ) -> ImportJob | None:
        """Return the oldest bounded notification retry candidate."""

        with self._lock:
            return _select_notification_retry(
                sorted(self._jobs.values(), key=lambda item: item.created_at),
                now,
                retry_after,
            )

    def commit_import(
        self, current: ImportJob, updated: ImportJob, commit: ImportCommit
    ) -> None:
        """Atomically register deterministic mappings in the test repository."""

        with self._lock:
            persisted = self.get(current.import_id)
            if persisted.state_version != current.state_version:
                raise ImportVersionConflict("Import job changed concurrently.")
            iris = {resource["resourceIri"] for resource in commit.resources}
            assets = {item.asset_id for item in commit.media}
            if iris & self._resource_iris or assets & self._asset_ids:
                raise ImportCommitConflict("A staging resource already exists.")
            self._resource_iris.update(iris)
            self._asset_ids.update(assets)
            self._jobs[current.import_id] = updated

    def _check_quota(
        self,
        candidate: ImportJob,
        quota_limit_bytes: int,
        *,
        excluding: str | None = None,
    ) -> None:
        used = sum(
            job.quota_reserved_bytes
            for job in self._jobs.values()
            if job.target.staging_area_iri == candidate.target.staging_area_iri
            and job.import_id != excluding
        )
        if used + candidate.quota_reserved_bytes > quota_limit_bytes:
            raise ImportQuotaExceededError("The staging-area quota is exhausted.")


class TransactionalConnection(Protocol):
    """Subset of the OLDAP connection required by this repository."""

    def query(self, query: str) -> Any: ...

    def transaction_start(self) -> None: ...

    def transaction_query(self, query: str) -> Any: ...

    def transaction_update(self, query: str) -> None: ...

    def transaction_commit(self) -> None: ...

    def transaction_abort(self) -> None: ...


class GraphDbImportJobRepository:
    """Store canonical ImportJob JSON with indexed facts in one named graph.

    Every create/replace operation performs its version and quota checks inside
    the same GraphDB transaction as the write. The JSON literal is canonical
    persisted state; indexed triples exist only for authorization, ordering,
    optimistic locking, and atomic staging-area quota sums.
    """

    def __init__(
        self,
        connection: TransactionalConnection,
        *,
        data_graph_resolver: Callable[[Any, str], URIRef] | None = None,
        media_ingest_base_url: str | None = None,
    ) -> None:
        self._connection = connection
        self._data_graph_resolver = (
            data_graph_resolver or resolve_project_data_graph_iri
        )
        self._media_base_url = (
            media_ingest_base_url
            or os.getenv("OLDAP_MEDIA_INGEST_URL", "https://media.oldap.org")
        ).rstrip("/")

    def create(self, job: ImportJob, *, quota_limit_bytes: int) -> None:
        self._connection.transaction_start()
        try:
            if self._exists(job.import_id, transactional=True):
                raise ImportVersionConflict("Import ID already exists.")
            self._check_quota(job, quota_limit_bytes, transactional=True)
            self._connection.transaction_update(self._insert(job))
            self._connection.transaction_commit()
        except Exception:
            self._connection.transaction_abort()
            raise

    def get(self, import_id: str) -> ImportJob:
        rows = _bindings(self._connection.query(self._select_one(import_id)))
        if not rows:
            raise ImportNotFoundError("Import job not found.")
        return ImportJob.from_dict(json.loads(rows[0]["payload"]["value"]))

    def list_for_owner(self, owner_iri: str) -> list[ImportJob]:
        query = f"""
SELECT ?payload ?created
WHERE {{
  GRAPH {IMPORT_GRAPH.n3()} {{
    ?job {RDF.type.n3()} {IMPORT_JOB_CLASS.n3()} ;
         {OWNER.n3()} {URIRef(owner_iri).n3()} ;
         {PAYLOAD.n3()} ?payload ;
         {CREATED_AT.n3()} ?created .
  }}
}}
ORDER BY DESC(?created) DESC(?job)
"""
        return [
            ImportJob.from_dict(json.loads(row["payload"]["value"]))
            for row in _bindings(self._connection.query(query))
        ]

    def replace(
        self,
        job: ImportJob,
        *,
        expected_state_version: int,
        quota_limit_bytes: int | None = None,
    ) -> None:
        self._connection.transaction_start()
        try:
            current = self._get_transactional(job.import_id)
            if current.state_version != expected_state_version:
                raise ImportVersionConflict("Import job changed concurrently.")
            if quota_limit_bytes is not None:
                self._check_quota(
                    job,
                    quota_limit_bytes,
                    transactional=True,
                    excluding=job.import_id,
                )
            self._connection.transaction_update(self._replace(current, job))
            self._connection.transaction_commit()
        except Exception:
            self._connection.transaction_abort()
            raise

    def claim_next(
        self,
        *,
        worker_id: str,
        supported_tasks: tuple[ImportTask, ...],
        claim_id: str,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> ImportJob | None:
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

    def get_by_claim(self, claim_id: str) -> ImportJob:
        query = f"""
SELECT ?payload
WHERE {{ GRAPH {IMPORT_GRAPH.n3()} {{
  ?job {ACTIVE_CLAIM.n3()} {Literal(claim_id).n3()} ; {PAYLOAD.n3()} ?payload .
}} }}
LIMIT 1
"""
        rows = _bindings(self._connection.query(query))
        if not rows:
            raise ImportNotFoundError("Import claim not found.")
        return ImportJob.from_dict(json.loads(rows[0]["payload"]["value"]))

    def next_notification_retry(
        self, *, now: datetime, retry_after: timedelta
    ) -> ImportJob | None:
        """Return the oldest bounded notification retry candidate."""

        return _select_notification_retry(
            self._all(transactional=False), now, retry_after
        )

    def commit_import(
        self, current: ImportJob, updated: ImportJob, commit: ImportCommit
    ) -> None:
        """Create all staging resources and IMPORTED state in one transaction."""

        data_graph_iri = self._data_graph_resolver(
            self._connection, current.target.project_short_name
        )
        self._connection.transaction_start()
        try:
            persisted = self._get_transactional(current.import_id)
            if (
                persisted.state_version != current.state_version
                or persisted.state is not ImportState.IMPORTING
                or persisted.active_claim_id != commit.claim_id
                or persisted.active_claim_task != ImportTask.IMPORT.value
            ):
                raise ImportVersionConflict("Import job changed concurrently.")
            context = self._commit_target_context(persisted, data_graph_iri)
            self._check_commit_collisions(persisted, commit, data_graph_iri)
            self._connection.transaction_update(
                _staging_insert(
                    persisted,
                    updated,
                    commit,
                    context,
                    data_graph_iri,
                    self._media_base_url,
                )
            )
            self._connection.transaction_update(self._replace(persisted, updated))
            self._connection.transaction_commit()
        except Exception:
            self._connection.transaction_abort()
            raise

    def _commit_target_context(
        self, job: ImportJob, data_graph_iri: URIRef
    ) -> dict[str, str]:
        rows = _bindings(
            self._connection.transaction_query(
                _commit_target_query(job, data_graph_iri)
            )
        )
        if not rows:
            raise ImportTargetNotFoundError(
                "The staging target or DATA_UPDATE authorization changed."
            )
        row = rows[0]
        if (
            row["areaName"]["value"] != job.target.staging_area_name
            or row["folderName"]["value"] != job.target.target_root_folder_name
        ):
            raise ImportTargetNotFoundError("The selected staging target changed.")
        admin = self._connection.transaction_query(_admin_create_query(job))
        if not bool(admin.get("boolean")):
            raise ImportPermissionDeniedError(
                "ADMIN_CREATE is no longer available for the selected project."
            )
        return {
            "defaultRole": row["defaultRole"]["value"],
            "defaultPermission": row["defaultPermission"]["value"],
        }

    def _check_commit_collisions(
        self,
        job: ImportJob,
        commit: ImportCommit,
        data_graph_iri: URIRef,
    ) -> None:
        rows = _bindings(
            self._connection.transaction_query(
                _direct_children_query(job, data_graph_iri)
            )
        )
        if len(rows) > 10_000:
            raise ImportCommitConflict("The target child inventory is too large.")
        children: dict[str, set[str]] = {}
        for row in rows:
            children.setdefault(_portable_name_key(row["name"]["value"]), set()).add(
                row["kind"]["value"]
            )
        folder_class = "http://oldap.org/shared#StagingFolder"
        for item in commit.folders:
            if (
                not item.parent_relative_path
                and _portable_name_key(item.name) in children
            ):
                raise ImportCommitConflict("A ZIP-root folder name now collides.")
        for item in commit.media:
            kinds = children.get(_portable_name_key(item.original_name), set())
            if not item.parent_relative_path and folder_class in kinds:
                raise ImportCommitConflict(
                    "A ZIP-root media name now collides with a folder."
                )
        if bool(
            self._connection.transaction_query(
                _resource_collision_query(job, commit, data_graph_iri)
            ).get("boolean")
        ):
            raise ImportCommitConflict(
                "A deterministic resource or asset already exists."
            )

    def _get_transactional(self, import_id: str) -> ImportJob:
        rows = _bindings(
            self._connection.transaction_query(self._select_one(import_id))
        )
        if not rows:
            raise ImportNotFoundError("Import job not found.")
        return ImportJob.from_dict(json.loads(rows[0]["payload"]["value"]))

    def _all(self, *, transactional: bool) -> list[ImportJob]:
        query = f"""
SELECT ?payload ?created
WHERE {{ GRAPH {IMPORT_GRAPH.n3()} {{
  ?job {RDF.type.n3()} {IMPORT_JOB_CLASS.n3()} ;
       {PAYLOAD.n3()} ?payload ; {CREATED_AT.n3()} ?created .
}} }}
ORDER BY ?created
"""
        result = (
            self._connection.transaction_query(query)
            if transactional
            else self._connection.query(query)
        )
        return [
            ImportJob.from_dict(json.loads(row["payload"]["value"]))
            for row in _bindings(result)
        ]

    def _exists(self, import_id: str, *, transactional: bool) -> bool:
        query = f"""
ASK {{ GRAPH {IMPORT_GRAPH.n3()} {{ {_job_iri(import_id).n3()} {RDF.type.n3()} {IMPORT_JOB_CLASS.n3()} }} }}
"""
        result = (
            self._connection.transaction_query(query)
            if transactional
            else self._connection.query(query)
        )
        return bool(result["boolean"])

    def _check_quota(
        self,
        job: ImportJob,
        quota_limit_bytes: int,
        *,
        transactional: bool,
        excluding: str | None = None,
    ) -> None:
        exclusion = f"FILTER(?job != {_job_iri(excluding).n3()})" if excluding else ""
        query = f"""
SELECT (COALESCE(SUM(?reserved), 0) AS ?used)
WHERE {{
  GRAPH {IMPORT_GRAPH.n3()} {{
    ?job {STAGING_AREA.n3()} {URIRef(job.target.staging_area_iri).n3()} ;
         {QUOTA_RESERVED.n3()} ?reserved .
    {exclusion}
  }}
}}
"""
        result = (
            self._connection.transaction_query(query)
            if transactional
            else self._connection.query(query)
        )
        rows = _bindings(result)
        used = int(rows[0]["used"]["value"]) if rows else 0
        if used + job.quota_reserved_bytes > quota_limit_bytes:
            raise ImportQuotaExceededError("The staging-area quota is exhausted.")

    @staticmethod
    def _select_one(import_id: str) -> str:
        return f"""
SELECT ?payload
WHERE {{
  GRAPH {IMPORT_GRAPH.n3()} {{
    {_job_iri(import_id).n3()} {PAYLOAD.n3()} ?payload .
  }}
}}
LIMIT 1
"""

    @staticmethod
    def _insert(job: ImportJob) -> str:
        return f"INSERT DATA {{ GRAPH {IMPORT_GRAPH.n3()} {{ {_job_triples(job)} }} }}"

    @staticmethod
    def _replace(current: ImportJob, updated: ImportJob) -> str:
        iri = _job_iri(current.import_id).n3()
        return f"""
DELETE {{ GRAPH {IMPORT_GRAPH.n3()} {{ {iri} ?property ?value . }} }}
INSERT {{ GRAPH {IMPORT_GRAPH.n3()} {{ {_job_triples(updated)} }} }}
WHERE  {{ GRAPH {IMPORT_GRAPH.n3()} {{
  {iri} {STATE_VERSION.n3()} {Literal(current.state_version).n3()} ;
        ?property ?value .
}} }}
"""


def _job_iri(import_id: str) -> URIRef:
    return URIRef(f"urn:oldap:import:{import_id}")


def _job_triples(job: ImportJob) -> str:
    payload = json.dumps(
        job.to_dict(internal=True),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    active_claim = (
        f"  {ACTIVE_CLAIM.n3()} {Literal(job.active_claim_id).n3()} ;\n"
        if job.active_claim_id
        else ""
    )
    return f"""
{_job_iri(job.import_id).n3()} {RDF.type.n3()} {IMPORT_JOB_CLASS.n3()} ;
  {PAYLOAD.n3()} {Literal(payload).n3()} ;
  {OWNER.n3()} {URIRef(job.requested_by_iri).n3()} ;
  {STAGING_AREA.n3()} {URIRef(job.target.staging_area_iri).n3()} ;
  {STATE_VERSION.n3()} {Literal(job.state_version, datatype=XSD.integer).n3()} ;
  {QUOTA_RESERVED.n3()} {Literal(job.quota_reserved_bytes, datatype=XSD.integer).n3()} ;
{active_claim}
  {CREATED_AT.n3()} {Literal(job.created_at, datatype=XSD.dateTime).n3()} .
"""


def _bindings(result: Any) -> list[dict[str, Any]]:
    return list(result.get("results", {}).get("bindings", []))


def _select_claim_candidate(
    jobs: list[ImportJob],
    supported_tasks: tuple[ImportTask, ...],
    now: datetime,
) -> ImportJob | None:
    if any(
        job.active_claim_id
        and job.active_claim_lease_expires_at
        and job.active_claim_lease_expires_at > now
        for job in jobs
    ):
        return None
    for task in (ImportTask.VALIDATE, ImportTask.IMPORT, ImportTask.CLEANUP):
        if task not in supported_tasks:
            continue
        for job in jobs:
            if _job_is_eligible(job, task, now):
                return job
    return None


def _select_notification_retry(
    jobs: list[ImportJob], now: datetime, retry_after: timedelta
) -> ImportJob | None:
    """Select at most one unsent notification without touching lifecycle state."""

    from .domain import NotificationStatus

    for job in jobs:
        if (
            job.notification_status
            in {NotificationStatus.PENDING, NotificationStatus.FAILED}
            and job.notification_attempts < 3
            and (
                job.notification_last_attempt_at is None
                or job.notification_last_attempt_at + retry_after <= now
            )
        ):
            return job
    return None


def _task_for_job(
    job: ImportJob, supported_tasks: tuple[ImportTask, ...], now: datetime
) -> ImportTask:
    for task in (ImportTask.VALIDATE, ImportTask.IMPORT, ImportTask.CLEANUP):
        if task in supported_tasks and _job_is_eligible(job, task, now):
            return task
    raise RuntimeError("Claim candidate has no eligible task.")


def _job_is_eligible(job: ImportJob, task: ImportTask, now: datetime) -> bool:
    from .domain import ImportState

    if task is ImportTask.VALIDATE:
        return job.state is ImportState.VALIDATING
    if task is ImportTask.IMPORT:
        return job.state is ImportState.IMPORTING
    if job.state is ImportState.IMPORTING:
        return False
    if job.cleanup_pending:
        return job.state in {
            ImportState.CANCELLED,
            ImportState.IMPORTED,
            ImportState.FAILED,
            ImportState.EXPIRED,
        }
    if job.state is ImportState.UPLOADING:
        return job.created_at + timedelta(hours=24) <= now
    return (
        job.state is ImportState.READY
        and job.expires_at is not None
        and job.expires_at <= now
    )


def _attach_claim(
    job: ImportJob,
    task: ImportTask,
    claim_id: str,
    worker_id: str,
    claimed_at: datetime,
    lease_expires_at: datetime,
) -> ImportJob:
    return replace(
        job,
        state_version=job.state_version + 1,
        updated_at=claimed_at,
        active_claim_id=claim_id,
        active_claim_task=task.value,
        active_claim_worker_id=worker_id,
        active_claimed_at=claimed_at,
        active_claim_lease_expires_at=lease_expires_at,
    )


def _commit_target_query(job: ImportJob, data_graph_iri: URIRef) -> str:
    """Resolve the live target, caller DATA_UPDATE, and inherited default role."""

    area = URIRef(job.target.staging_area_iri).n3()
    folder = URIRef(job.target.target_root_folder_iri).n3()
    user = URIRef(job.requested_by_iri).n3()
    data_graph = data_graph_iri.n3()
    return f"""
PREFIX oldap: <http://oldap.org/base#>
PREFIX shared: <http://oldap.org/shared#>
PREFIX schema: <https://schema.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?areaName ?folderName ?defaultRole ?defaultPermission
WHERE {{
  GRAPH {data_graph} {{
    {area} a ?areaClass ; schema:name ?areaName ;
      shared:stagingDefaultRole ?defaultRole ; oldap:attachedToRole ?effectiveRole .
    << {area} oldap:attachedToRole ?effectiveRole >>
      oldap:hasDataPermission ?effectivePermission .
    << {area} oldap:attachedToRole ?defaultRole >>
      oldap:hasDataPermission ?defaultPermission .
    {folder} a shared:StagingFolder ; shared:inStagingArea {area} ;
      schema:name ?folderName .
  }}
  FILTER(
    ?areaClass = shared:StagingArea ||
    EXISTS {{ GRAPH ?areaOntology {{
      ?areaClass rdfs:subClassOf+ shared:StagingArea .
    }} }}
  )
  GRAPH oldap:admin {{
    {user} oldap:hasRole ?effectiveRole .
    ?effectivePermission oldap:permissionValue ?permissionValue .
    FILTER(xsd:integer(?permissionValue) >= 4)
  }}
}}
LIMIT 1
"""


def _admin_create_query(job: ImportJob) -> str:
    """Recheck the original user's project/global create permission."""

    user = URIRef(job.requested_by_iri).n3()
    # OLDAP stores project short names as xsd:NCName. A plain/string literal
    # does not RDF-match that value and would incorrectly revoke ADMIN_CREATE
    # during the final, transactional authorization check.
    project = Literal(job.target.project_short_name, datatype=XSD.NCName).n3()
    return f"""
PREFIX oldap: <http://oldap.org/base#>
ASK {{ GRAPH oldap:admin {{
  {{
    ?project a oldap:Project ; oldap:projectShortName {project} .
    << {user} oldap:inProject ?project >> oldap:hasAdminPermission oldap:ADMIN_CREATE .
  }} UNION {{
    << {user} oldap:inProject ?anyProject >> oldap:hasAdminPermission oldap:ADMIN_OLDAP .
  }}
}} }}
"""


def _direct_children_query(job: ImportJob, data_graph_iri: URIRef) -> str:
    area = URIRef(job.target.staging_area_iri).n3()
    folder = URIRef(job.target.target_root_folder_iri).n3()
    data_graph = data_graph_iri.n3()
    return f"""
PREFIX shared: <http://oldap.org/shared#>
PREFIX schema: <https://schema.org/>
SELECT ?kind ?name WHERE {{ GRAPH {data_graph} {{
  ?child shared:inStagingFolder {folder} ; shared:inStagingArea {area} ; a ?kind .
  VALUES ?kind {{ shared:StagingFolder shared:StagingMediaObject }}
  OPTIONAL {{ ?child schema:name ?schemaName . }}
  OPTIONAL {{ ?child shared:originalName ?originalName . }}
  BIND(COALESCE(?originalName, ?schemaName) AS ?name)
}} }}
LIMIT 10001
"""


def _resource_collision_query(
    job: ImportJob, commit: ImportCommit, data_graph_iri: URIRef
) -> str:
    iris = " ".join(URIRef(item["resourceIri"]).n3() for item in commit.resources)
    assets = " ".join(Literal(item.asset_id).n3() for item in commit.media)
    data_graph = data_graph_iri.n3()
    return f"""
PREFIX shared: <http://oldap.org/shared#>
ASK {{ GRAPH {data_graph} {{
  {{ VALUES ?resource {{ {iris} }} ?resource ?property ?value . }}
  UNION
  {{ VALUES ?assetId {{ {assets} }} ?existing shared:assetId ?assetId . }}
}} }}
"""


def _staging_insert(
    job: ImportJob,
    updated: ImportJob,
    commit: ImportCommit,
    context: dict[str, str],
    data_graph_iri: URIRef,
    media_base_url: str,
) -> str:
    """Build the single resource INSERT used inside the job transaction."""

    area = URIRef(job.target.staging_area_iri).n3()
    user = URIRef(job.requested_by_iri).n3()
    role = URIRef(context["defaultRole"]).n3()
    permission = URIRef(context["defaultPermission"]).n3()
    data_graph = data_graph_iri.n3()
    # The inherited oldap:Thing audit properties require xsd:dateTimeStamp.
    # Using xsd:dateTime makes oldaplib deserialize the stored value into the
    # wrong wrapper type and prevents the imported resource from being read.
    timestamp = Literal(updated.updated_at, datatype=XSD.dateTimeStamp).n3()
    folders = {item.relative_path: item.resource_iri for item in commit.folders}
    triples: list[str] = []

    def metadata(iri: str) -> str:
        return (
            f"{iri} oldap:createdBy {user} ; oldap:creationDate {timestamp} ; "
            f"oldap:lastModifiedBy {user} ; oldap:lastModificationDate {timestamp} ; "
            f"oldap:attachedToRole {role} .\n"
            f"<< {iri} oldap:attachedToRole {role} >> "
            f"oldap:hasDataPermission {permission} ."
        )

    for item in commit.folders:
        iri = URIRef(item.resource_iri).n3()
        parent = URIRef(
            folders.get(item.parent_relative_path, job.target.target_root_folder_iri)
        ).n3()
        triples.append(
            f"{iri} a shared:StagingFolder ; schema:name {Literal(item.name).n3()} ; "
            f"shared:inStagingArea {area} ; shared:inStagingFolder {parent} .\n"
            + metadata(iri)
        )
    for item in commit.media:
        iri = URIRef(item.resource_iri).n3()
        server_url = (
            f"{media_base_url}/iiif/3/"
            if item.protocol == "iiif"
            else f"{media_base_url}/"
        )
        parent = URIRef(
            folders.get(item.parent_relative_path, job.target.target_root_folder_iri)
        ).n3()
        triples.append(
            f"{iri} a shared:StagingMediaObject ; "
            f'dcterms:type {item.dcterms_type} ; shared:mediaAccessMode "local" ; '
            f"shared:originalName {Literal(item.original_name).n3()} ; "
            f"shared:originalMimeType {Literal(item.original_mime_type).n3()} ; "
            f"shared:checksum {Literal(item.checksum_sha256).n3()} ; "
            f"shared:assetId {Literal(item.asset_id).n3()} ; "
            f"shared:protocol {Literal(item.protocol).n3()} ; "
            f"shared:serverUrl {Literal(server_url).n3()} ; "
            f"shared:derivativeName {Literal(item.derivative_name).n3()} ; "
            f"shared:path {Literal(item.storage_path).n3()} ; "
            f"shared:inStagingArea {area} ; shared:inStagingFolder {parent} ; "
            f"shared:stagingStatus shared:StagingStatusNew .\n" + metadata(iri)
        )
    body = "\n".join(triples)
    return f"""
PREFIX oldap: <http://oldap.org/base#>
PREFIX shared: <http://oldap.org/shared#>
PREFIX schema: <https://schema.org/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX dcmitype: <http://purl.org/dc/dcmitype/>
INSERT DATA {{ GRAPH {data_graph} {{
{body}
}} }}
"""


def _portable_name_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).rstrip(" .").casefold()
