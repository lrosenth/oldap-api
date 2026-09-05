"""Durable GraphDB outbox for mobile-origin staging-media lifecycle events."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD

from .repository import (
    CLIENT_ASSET_ID,
    OWNER,
    RECEIPT_CLASS,
    RECEIPT_GRAPH,
    RESOURCE,
    STAGING_AREA,
    UPLOAD_ID,
)

LIFECYCLE_EVENT_CLASS = URIRef("urn:oldap:mobile-media:LifecycleEvent")
LIFECYCLE_EVENT_ID = URIRef("urn:oldap:mobile-media:lifecycleEventId")
LIFECYCLE_KIND = URIRef("urn:oldap:mobile-media:lifecycleKind")
LIFECYCLE_RECEIPT = URIRef("urn:oldap:mobile-media:lifecycleReceipt")
LIFECYCLE_CHECKSUM = URIRef("urn:oldap:mobile-media:lifecycleChecksum")
LIFECYCLE_STATE = URIRef("urn:oldap:mobile-media:lifecycleState")
LIFECYCLE_CREATED_AT = URIRef("urn:oldap:mobile-media:lifecycleCreatedAt")
LIFECYCLE_ATTEMPTS = URIRef("urn:oldap:mobile-media:lifecycleAttempts")
LIFECYCLE_CLAIM_ID = URIRef("urn:oldap:mobile-media:lifecycleClaimId")
LIFECYCLE_WORKER_ID = URIRef("urn:oldap:mobile-media:lifecycleWorkerId")
LIFECYCLE_LEASE_EXPIRES_AT = URIRef("urn:oldap:mobile-media:lifecycleLeaseExpiresAt")
LIFECYCLE_COMPLETED_AT = URIRef("urn:oldap:mobile-media:lifecycleCompletedAt")

LIFECYCLE_KINDS = frozenset({"moved", "staging_deleted", "archived"})
CHECKSUM_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
WORKER_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class LifecycleConnection(Protocol):
    """Minimal active-transaction surface used by the outbox."""

    def transaction_start(self) -> None: ...

    def transaction_query(self, query: str) -> Any: ...

    def transaction_update(self, query: str) -> None: ...

    def transaction_commit(self) -> None: ...

    def transaction_abort(self) -> None: ...


class MobileMediaLifecycleError(RuntimeError):
    """Reject malformed, stale, or unavailable internal lifecycle work."""


@dataclass(frozen=True, slots=True)
class MobileMediaLifecycleClaim:
    """One immutable outbox event protected by a renewable-by-reclaim lease."""

    event_id: str
    claim_id: str
    worker_id: str
    kind: str
    upload_id: str
    client_asset_id: str
    owner_user_iri: str
    staging_area_id: str
    resource_iri: str
    checksum: str
    occurred_at: datetime
    lease_expires_at: datetime

    def to_dict(self) -> dict[str, str]:
        """Return the closed media-worker transport representation."""

        return {
            "eventId": self.event_id,
            "claimId": self.claim_id,
            "workerId": self.worker_id,
            "kind": self.kind,
            "uploadId": self.upload_id,
            "clientAssetId": self.client_asset_id,
            "ownerUserIri": self.owner_user_iri,
            "stagingAreaId": self.staging_area_id,
            "resourceIri": self.resource_iri,
            "checksum": self.checksum,
            "occurredAt": _timestamp(self.occurred_at),
            "leaseExpiresAt": _timestamp(self.lease_expires_at),
        }


class GraphDbMobileMediaLifecycleOutbox:
    """Append lifecycle facts transactionally and lease them to the media worker."""

    def __init__(self, connection: LifecycleConnection, *, lease_seconds: int = 300):
        if lease_seconds <= 0:
            raise ValueError("Lifecycle lease duration must be positive.")
        self._connection = connection
        self._lease_seconds = lease_seconds

    def append_to_active_transaction(
        self,
        *,
        event_id: str,
        kind: str,
        resource_iri: str,
        checksum: str,
        occurred_at: datetime,
    ) -> None:
        """Append an event only when the resource has a mobile commit receipt.

        The caller owns the active GraphDB transaction. No event is emitted for
        legacy or non-mobile staging media.
        """

        event_id = _uuid(event_id, "eventId")
        if kind not in LIFECYCLE_KINDS:
            raise ValueError("Unsupported mobile-media lifecycle kind.")
        if CHECKSUM_RE.fullmatch(checksum) is None:
            raise ValueError("Lifecycle checksum must be canonical SHA-256.")
        event = URIRef(f"urn:oldap:mobile-media-lifecycle:{event_id}").n3()
        resource = Literal(resource_iri, datatype=XSD.anyURI).n3()
        self._connection.transaction_update(f"""
INSERT {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    {event} a {LIFECYCLE_EVENT_CLASS.n3()} ;
      {LIFECYCLE_EVENT_ID.n3()} {Literal(event_id).n3()} ;
      {LIFECYCLE_KIND.n3()} {Literal(kind).n3()} ;
      {LIFECYCLE_RECEIPT.n3()} ?receipt ;
      {UPLOAD_ID.n3()} ?uploadId ;
      {CLIENT_ASSET_ID.n3()} ?clientAssetId ;
      {OWNER.n3()} ?owner ;
      {STAGING_AREA.n3()} ?stagingArea ;
      {RESOURCE.n3()} {resource} ;
      {LIFECYCLE_CHECKSUM.n3()} {Literal(checksum).n3()} ;
      {LIFECYCLE_STATE.n3()} "pending" ;
      {LIFECYCLE_CREATED_AT.n3()} {Literal(occurred_at.astimezone(UTC), datatype=XSD.dateTimeStamp).n3()} ;
      {LIFECYCLE_ATTEMPTS.n3()} 0 .
  }}
}}
WHERE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    ?receipt a {RECEIPT_CLASS.n3()} ;
      {UPLOAD_ID.n3()} ?uploadId ;
      {CLIENT_ASSET_ID.n3()} ?clientAssetId ;
      {OWNER.n3()} ?owner ;
      {STAGING_AREA.n3()} ?stagingArea ;
      {RESOURCE.n3()} ?storedResource .
    FILTER(STR(?storedResource) = STR({resource}))
    FILTER NOT EXISTS {{ ?existing {LIFECYCLE_EVENT_ID.n3()} {Literal(event_id).n3()} . }}
  }}
}}
""")

    def normalize_legacy_resource_reference(self, resource_iri: str) -> bool:
        """Convert internal legacy IRI links into non-referential URI metadata.

        Early Step-13D receipts represented ``resource`` as an RDF IRI object.
        OLDAP's generic in-use guard correctly treated that internal edge as a
        live reference and therefore blocked deletion of the staging resource.
        This narrowly scoped migration runs only after a delete attempt has
        already passed permission checks and found an in-use conflict. It keeps
        every receipt fact while ensuring the private audit graph does not
        participate in application referential integrity.
        """

        resource = URIRef(resource_iri).n3()
        resource_text = Literal(resource_iri, datatype=XSD.anyURI).n3()
        self._connection.transaction_start()
        try:
            rows = _bindings(
                self._connection.transaction_query(
                    _legacy_resource_receipt_query(resource_iri)
                )
            )
            if not rows:
                self._connection.transaction_commit()
                return False
            if len(rows) != 1:
                raise MobileMediaLifecycleError(
                    "Mobile-media resource receipt is contradictory."
                )
            receipt = rows[0].get("receipt")
            stored_resource = rows[0].get("resource")
            if (
                not isinstance(receipt, dict)
                or receipt.get("type") != "uri"
                or not isinstance(receipt.get("value"), str)
                or not isinstance(stored_resource, dict)
                or stored_resource.get("value") != resource_iri
                or stored_resource.get("type") not in {"uri", "literal"}
            ):
                raise MobileMediaLifecycleError(
                    "Mobile-media resource receipt is invalid."
                )
            receipt_prefix = "urn:oldap:mobile-media-commit:"
            receipt_value = receipt["value"]
            if not receipt_value.startswith(receipt_prefix):
                raise MobileMediaLifecycleError(
                    "Mobile-media resource receipt is invalid."
                )
            _uuid(receipt_value.removeprefix(receipt_prefix), "clientAssetId")
            receipt_iri = URIRef(receipt_value).n3()
            if stored_resource.get("type") == "literal" and stored_resource.get(
                "datatype"
            ) != str(XSD.anyURI):
                raise MobileMediaLifecycleError(
                    "Mobile-media resource receipt is invalid."
                )
            self._connection.transaction_update(f"""
DELETE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    ?subject {RESOURCE.n3()} {resource} .
  }}
}}
INSERT {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    ?subject {RESOURCE.n3()} {resource_text} .
  }}
}}
WHERE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    {receipt_iri} a {RECEIPT_CLASS.n3()} .
    ?subject {RESOURCE.n3()} {resource} .
  }}
}}
""")
            self._connection.transaction_commit()
            return True
        except Exception:
            self._connection.transaction_abort()
            raise

    def claim_next(
        self, worker_id: str, *, now: datetime | None = None
    ) -> MobileMediaLifecycleClaim | None:
        """Lease the oldest pending or expired event in one transaction."""

        if WORKER_ID_RE.fullmatch(worker_id) is None:
            raise ValueError("Lifecycle workerId is invalid.")
        claimed_at = (now or datetime.now(UTC)).astimezone(UTC)
        lease_expires_at = claimed_at + timedelta(seconds=self._lease_seconds)
        claim_id = str(uuid4())
        self._connection.transaction_start()
        try:
            rows = _bindings(
                self._connection.transaction_query(_claim_candidate_query(claimed_at))
            )
            if not rows:
                self._connection.transaction_commit()
                return None
            if len(rows) != 1:
                raise MobileMediaLifecycleError("Lifecycle outbox is contradictory.")
            claim = _claim_from_row(
                rows[0],
                claim_id=claim_id,
                worker_id=worker_id,
                lease_expires_at=lease_expires_at,
            )
            self._connection.transaction_update(
                _claim_update(claim, claimed_at=claimed_at)
            )
            self._connection.transaction_commit()
            return claim
        except Exception:
            self._connection.transaction_abort()
            raise

    def complete(
        self,
        event_id: str,
        claim_id: str,
        worker_id: str,
        *,
        completed_at: datetime | None = None,
    ) -> None:
        """Acknowledge the exact active claim; duplicate completion is harmless."""

        event_id = _uuid(event_id, "eventId")
        claim_id = _uuid(claim_id, "claimId")
        if WORKER_ID_RE.fullmatch(worker_id) is None:
            raise ValueError("Lifecycle workerId is invalid.")
        timestamp = (completed_at or datetime.now(UTC)).astimezone(UTC)
        self._connection.transaction_start()
        try:
            rows = _bindings(
                self._connection.transaction_query(_event_state_query(event_id))
            )
            if len(rows) != 1:
                raise MobileMediaLifecycleError("Lifecycle event was not found.")
            row = rows[0]
            state = _value(row, "state")
            if state == "delivered":
                if (
                    _value(row, "claimId") != claim_id
                    or _value(row, "workerId") != worker_id
                ):
                    raise MobileMediaLifecycleError(
                        "Lifecycle completion claim is stale."
                    )
                self._connection.transaction_commit()
                return
            if (
                state != "claimed"
                or _value(row, "claimId") != claim_id
                or _value(row, "workerId") != worker_id
            ):
                raise MobileMediaLifecycleError("Lifecycle claim is stale.")
            self._connection.transaction_update(
                _completion_update(event_id, claim_id, worker_id, timestamp)
            )
            self._connection.transaction_commit()
        except Exception:
            self._connection.transaction_abort()
            raise


def _legacy_resource_receipt_query(resource_iri: str) -> str:
    resource = Literal(resource_iri, datatype=XSD.anyURI).n3()
    return f"""
SELECT ?receipt ?resource
WHERE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    ?receipt a {RECEIPT_CLASS.n3()} ;
      {RESOURCE.n3()} ?resource .
    FILTER(STR(?resource) = STR({resource}))
  }}
}}
LIMIT 2
"""


def _claim_candidate_query(now: datetime) -> str:
    return f"""
SELECT ?event ?eventId ?kind ?uploadId ?clientAssetId ?owner ?stagingArea
       ?resource ?checksum ?createdAt ?state ?leaseExpiresAt
WHERE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    ?event a {LIFECYCLE_EVENT_CLASS.n3()} ;
      {LIFECYCLE_EVENT_ID.n3()} ?eventId ;
      {LIFECYCLE_KIND.n3()} ?kind ;
      {UPLOAD_ID.n3()} ?uploadId ;
      {CLIENT_ASSET_ID.n3()} ?clientAssetId ;
      {OWNER.n3()} ?owner ;
      {STAGING_AREA.n3()} ?stagingArea ;
      {RESOURCE.n3()} ?resource ;
      {LIFECYCLE_CHECKSUM.n3()} ?checksum ;
      {LIFECYCLE_CREATED_AT.n3()} ?createdAt ;
      {LIFECYCLE_STATE.n3()} ?state .
    OPTIONAL {{ ?event {LIFECYCLE_LEASE_EXPIRES_AT.n3()} ?leaseExpiresAt . }}
    FILTER(?state = "pending" || (?state = "claimed" && ?leaseExpiresAt <= {Literal(now, datatype=XSD.dateTimeStamp).n3()}))
  }}
}}
ORDER BY ?createdAt ?eventId
LIMIT 1
"""


def _claim_update(claim: MobileMediaLifecycleClaim, *, claimed_at: datetime) -> str:
    event = URIRef(f"urn:oldap:mobile-media-lifecycle:{claim.event_id}").n3()
    return f"""
DELETE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    {event} {LIFECYCLE_STATE.n3()} ?oldState ;
      {LIFECYCLE_ATTEMPTS.n3()} ?oldAttempts .
    {event} {LIFECYCLE_CLAIM_ID.n3()} ?oldClaimId .
    {event} {LIFECYCLE_WORKER_ID.n3()} ?oldWorkerId .
    {event} {LIFECYCLE_LEASE_EXPIRES_AT.n3()} ?oldLease .
  }}
}}
INSERT {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    {event} {LIFECYCLE_STATE.n3()} "claimed" ;
      {LIFECYCLE_ATTEMPTS.n3()} ?nextAttempts ;
      {LIFECYCLE_CLAIM_ID.n3()} {Literal(claim.claim_id).n3()} ;
      {LIFECYCLE_WORKER_ID.n3()} {Literal(claim.worker_id).n3()} ;
      {LIFECYCLE_LEASE_EXPIRES_AT.n3()} {Literal(claim.lease_expires_at, datatype=XSD.dateTimeStamp).n3()} .
  }}
}}
WHERE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    {event} {LIFECYCLE_STATE.n3()} ?oldState ;
      {LIFECYCLE_ATTEMPTS.n3()} ?oldAttempts .
    OPTIONAL {{ {event} {LIFECYCLE_CLAIM_ID.n3()} ?oldClaimId . }}
    OPTIONAL {{ {event} {LIFECYCLE_WORKER_ID.n3()} ?oldWorkerId . }}
    OPTIONAL {{ {event} {LIFECYCLE_LEASE_EXPIRES_AT.n3()} ?oldLease . }}
    FILTER(?oldState = "pending" || (?oldState = "claimed" && ?oldLease <= {Literal(claimed_at, datatype=XSD.dateTimeStamp).n3()}))
    BIND(?oldAttempts + 1 AS ?nextAttempts)
  }}
}}
"""


def _event_state_query(event_id: str) -> str:
    event = URIRef(f"urn:oldap:mobile-media-lifecycle:{event_id}").n3()
    return f"""
SELECT ?state ?claimId ?workerId
WHERE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    {event} {LIFECYCLE_STATE.n3()} ?state .
    OPTIONAL {{ {event} {LIFECYCLE_CLAIM_ID.n3()} ?claimId . }}
    OPTIONAL {{ {event} {LIFECYCLE_WORKER_ID.n3()} ?workerId . }}
  }}
}}
LIMIT 2
"""


def _completion_update(
    event_id: str, claim_id: str, worker_id: str, completed_at: datetime
) -> str:
    event = URIRef(f"urn:oldap:mobile-media-lifecycle:{event_id}").n3()
    return f"""
DELETE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    {event} {LIFECYCLE_STATE.n3()} "claimed" ;
      {LIFECYCLE_LEASE_EXPIRES_AT.n3()} ?lease .
  }}
}}
INSERT {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    {event} {LIFECYCLE_STATE.n3()} "delivered" ;
      {LIFECYCLE_COMPLETED_AT.n3()} {Literal(completed_at, datatype=XSD.dateTimeStamp).n3()} .
  }}
}}
WHERE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    {event} {LIFECYCLE_STATE.n3()} "claimed" ;
      {LIFECYCLE_CLAIM_ID.n3()} {Literal(claim_id).n3()} ;
      {LIFECYCLE_WORKER_ID.n3()} {Literal(worker_id).n3()} ;
      {LIFECYCLE_LEASE_EXPIRES_AT.n3()} ?lease .
  }}
}}
"""


def _claim_from_row(
    row: dict[str, Any], *, claim_id: str, worker_id: str, lease_expires_at: datetime
) -> MobileMediaLifecycleClaim:
    try:
        occurred_at = datetime.fromisoformat(
            _value(row, "createdAt").replace("Z", "+00:00")
        )
        claim = MobileMediaLifecycleClaim(
            event_id=_uuid(_value(row, "eventId"), "eventId"),
            claim_id=claim_id,
            worker_id=worker_id,
            kind=_value(row, "kind"),
            upload_id=_uuid(_value(row, "uploadId"), "uploadId"),
            client_asset_id=_uuid(_value(row, "clientAssetId"), "clientAssetId"),
            owner_user_iri=_value(row, "owner"),
            staging_area_id=_value(row, "stagingArea"),
            resource_iri=_value(row, "resource"),
            checksum=_value(row, "checksum"),
            occurred_at=occurred_at,
            lease_expires_at=lease_expires_at,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise MobileMediaLifecycleError(
            "Lifecycle outbox record is invalid."
        ) from error
    if (
        claim.kind not in LIFECYCLE_KINDS
        or CHECKSUM_RE.fullmatch(claim.checksum) is None
    ):
        raise MobileMediaLifecycleError("Lifecycle outbox record is invalid.")
    return claim


def _bindings(value: Any) -> list[dict[str, Any]]:
    try:
        bindings = value["results"]["bindings"]
    except (KeyError, TypeError) as error:
        raise MobileMediaLifecycleError(
            "GraphDB returned an invalid result."
        ) from error
    if not isinstance(bindings, list) or not all(
        isinstance(row, dict) for row in bindings
    ):
        raise MobileMediaLifecycleError("GraphDB returned an invalid result.")
    return bindings


def _value(row: dict[str, Any], name: str) -> str:
    value = row[name]["value"]
    if not isinstance(value, str) or not value:
        raise ValueError(f"Lifecycle field {name} is invalid.")
    return value


def _uuid(value: str, field: str) -> str:
    parsed = UUID(str(value))
    if str(parsed) != str(value) or parsed.int == 0:
        raise ValueError(f"Lifecycle {field} is invalid.")
    return str(parsed)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
