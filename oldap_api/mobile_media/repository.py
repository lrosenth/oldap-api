"""Transactional GraphDB persistence for atomic mobile-media commits."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlsplit

import rfc8785
from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD

from .domain import (
    MobileMediaCommit,
    MobileMediaCommitConflict,
    MobileMediaCommitResult,
    MobileMediaDestinationChangedError,
    MobileMediaInboxNotFoundError,
    MobileMediaInboxNotProtectedError,
    MobileMediaPermissionDeniedError,
    MobileMediaServiceUnavailableError,
    MobileMediaUploadPermissionDeniedError,
    validated_relative_storage_path,
)

RECEIPT_GRAPH = URIRef("urn:oldap:mobile-media-commits")
RECEIPT_CLASS = URIRef("urn:oldap:mobile-media:CommitReceipt")
UPLOAD_ID = URIRef("urn:oldap:mobile-media:uploadId")
CLIENT_ASSET_ID = URIRef("urn:oldap:mobile-media:clientAssetId")
EVENT_ID = URIRef("urn:oldap:mobile-media:eventId")
REQUEST_DIGEST = URIRef("urn:oldap:mobile-media:requestDigest")
OWNER = URIRef("urn:oldap:mobile-media:owner")
STAGING_AREA = URIRef("urn:oldap:mobile-media:stagingArea")
RESOURCE = URIRef("urn:oldap:mobile-media:resource")
RESULT = URIRef("urn:oldap:mobile-media:result")

DATA_VIEW_IRI = "http://oldap.org/base#DATA_VIEW"
PROJECT_SHORT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


class TransactionalConnection(Protocol):
    """Minimal oldaplib connection surface used by this repository."""

    def transaction_start(self) -> None: ...

    def transaction_query(self, query: str) -> Any: ...

    def transaction_update(self, query: str) -> None: ...

    def transaction_commit(self) -> None: ...

    def transaction_abort(self) -> None: ...


@dataclass(frozen=True, slots=True)
class MobileMediaTarget:
    """Server-resolved live destination facts used for one resource insert."""

    data_graph_iri: str
    project_iri: str
    project_short_name: str
    default_role_iri: str
    media_path: str
    mobile_folder_iri: str

    @property
    def storage_path(self) -> str:
        """Return the media-server base path derived from trusted OLDAP facts."""

        try:
            media_path = validated_relative_storage_path(self.media_path)
        except ValueError as error:
            raise MobileMediaServiceUnavailableError(
                "The staging media path is invalid."
            ) from error
        if PROJECT_SHORT_NAME_RE.fullmatch(self.project_short_name) is None:
            raise MobileMediaServiceUnavailableError(
                "The staging project short name is invalid."
            )
        return f"{self.project_short_name}/image/{media_path}"


class GraphDbMobileMediaRepository:
    """Create a staging resource and permanent receipt in one transaction."""

    def __init__(
        self,
        connection: TransactionalConnection,
        *,
        media_ingest_base_url: str | None = None,
    ) -> None:
        self._connection = connection
        media_base_url = (
            media_ingest_base_url
            or os.getenv("OLDAP_MEDIA_INGEST_URL", "https://media.oldap.org")
        ).rstrip("/")
        parsed_media_url = urlsplit(media_base_url)
        if (
            parsed_media_url.scheme not in {"https", "http"}
            or not parsed_media_url.netloc
            or parsed_media_url.username is not None
            or parsed_media_url.password is not None
            or parsed_media_url.query
            or parsed_media_url.fragment
            or any(character.isspace() for character in media_base_url)
        ):
            raise MobileMediaServiceUnavailableError(
                "The media delivery origin is invalid."
            )
        self._media_base_url = media_base_url

    def commit(
        self,
        commit: MobileMediaCommit,
        *,
        committed_at: datetime | None = None,
    ) -> MobileMediaCommitResult:
        """Create or exactly replay one atomic mobile-media registration."""

        timestamp = (committed_at or datetime.now(UTC)).astimezone(UTC)
        self._connection.transaction_start()
        try:
            replay = self._existing_receipt(commit)
            if replay is not None:
                self._connection.transaction_commit()
                return replay

            target = self._resolve_target(commit)
            if commit.publication.storage_path != target.storage_path:
                raise MobileMediaDestinationChangedError(
                    "The published media path no longer matches the StagingArea."
                )
            if not _ask(
                self._connection.transaction_query(
                    _admin_create_query(commit, target.project_iri)
                )
            ):
                raise MobileMediaUploadPermissionDeniedError(
                    "Current media creation permission is unavailable."
                )
            target = self._resolve_inbox(commit, target)
            if _ask(
                self._connection.transaction_query(_resource_collision_query(commit))
            ):
                raise MobileMediaCommitConflict(
                    "The mobile-media identity conflicts with existing data."
                )

            result = MobileMediaCommitResult(
                event_id=commit.event_id,
                upload_id=commit.upload_id,
                client_asset_id=commit.client_asset_id,
                staging_area_id=commit.staging_area_id,
                asset_id=commit.client_asset_id,
                resource_iri=commit.resource_iri,
                checksum=commit.checksum,
                committed_at=timestamp,
            )
            self._connection.transaction_update(
                _atomic_insert(
                    commit,
                    result,
                    target,
                    media_base_url=self._media_base_url,
                )
            )
            self._connection.transaction_commit()
            return result
        except Exception:
            self._connection.transaction_abort()
            raise

    def _existing_receipt(
        self, commit: MobileMediaCommit
    ) -> MobileMediaCommitResult | None:
        rows = _bindings(self._connection.transaction_query(_receipt_query(commit)))
        if not rows:
            return None
        if len(rows) != 1:
            raise MobileMediaCommitConflict(
                "The mobile-media identity conflicts with existing data."
            )
        row = rows[0]
        try:
            receipt_iri = row["receipt"]["value"]
            event_id = row["eventId"]["value"]
            request_digest = row["requestDigest"]["value"]
            owner = row["owner"]["value"]
            staging_area = row["stagingArea"]["value"]
            resource = row["resource"]["value"]
            result = MobileMediaCommitResult.from_dict(
                json.loads(row["result"]["value"])
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise MobileMediaServiceUnavailableError(
                "The permanent mobile-media receipt is invalid."
            ) from error
        if (
            receipt_iri != commit.receipt_iri
            or event_id != commit.event_id
            or request_digest != commit.request_digest
            or owner != commit.owner_user_iri
            or staging_area != commit.staging_area_id
            or resource != commit.resource_iri
            or result.event_id != commit.event_id
            or result.upload_id != commit.upload_id
            or result.client_asset_id != commit.client_asset_id
            or result.asset_id != commit.client_asset_id
            or result.staging_area_id != commit.staging_area_id
            or result.resource_iri != commit.resource_iri
            or result.checksum != commit.checksum
        ):
            raise MobileMediaCommitConflict(
                "The mobile-media identity conflicts with existing data."
            )
        return result

    def _resolve_target(self, commit: MobileMediaCommit) -> MobileMediaTarget:
        rows = _bindings(self._connection.transaction_query(_target_query(commit)))
        if len(rows) != 1:
            raise MobileMediaPermissionDeniedError(
                "The account is not permitted to use the selected StagingArea."
            )
        row = rows[0]
        try:
            target = MobileMediaTarget(
                data_graph_iri=row["dataGraph"]["value"],
                project_iri=row["project"]["value"],
                project_short_name=row["projectShortName"]["value"],
                default_role_iri=row["defaultRole"]["value"],
                media_path=row["mediaPath"]["value"],
                mobile_folder_iri="",
            )
            target.storage_path
        except (KeyError, TypeError) as error:
            raise MobileMediaServiceUnavailableError(
                "The StagingArea context is incomplete."
            ) from error
        return target

    def _resolve_inbox(
        self, commit: MobileMediaCommit, target: MobileMediaTarget
    ) -> MobileMediaTarget:
        rows = _bindings(
            self._connection.transaction_query(_inbox_query(commit, target))
        )
        if not rows:
            raise MobileMediaInboxNotFoundError(
                "The protected mobile inbox was not found."
            )
        if len(rows) != 1:
            raise MobileMediaInboxNotProtectedError(
                "The protected mobile inbox is ambiguous."
            )
        row = rows[0]
        if "mobile" not in row:
            raise MobileMediaInboxNotFoundError(
                "The protected mobile inbox was not found."
            )
        try:
            role = row["mobileRole"]["value"]
            permission = row["mobilePermission"]["value"]
            mobile = row["mobile"]["value"]
        except (KeyError, TypeError) as error:
            raise MobileMediaInboxNotProtectedError(
                "The mobile inbox has no complete read-only role policy."
            ) from error
        if role != target.default_role_iri or permission != DATA_VIEW_IRI:
            raise MobileMediaInboxNotProtectedError(
                "The mobile inbox is not protected by the default read-only role."
            )
        return replace(target, mobile_folder_iri=mobile)


def _bindings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        raise MobileMediaServiceUnavailableError(
            "GraphDB returned an invalid query result."
        )
    results = value.get("results")
    if not isinstance(results, dict):
        raise MobileMediaServiceUnavailableError(
            "GraphDB returned an invalid query result."
        )
    bindings = results.get("bindings")
    if not isinstance(bindings, list) or not all(
        isinstance(binding, dict) for binding in bindings
    ):
        raise MobileMediaServiceUnavailableError(
            "GraphDB returned an invalid query result."
        )
    return bindings


def _ask(value: Any) -> bool:
    """Accept only the native JSON boolean returned by a SPARQL ASK query."""

    if not isinstance(value, dict) or type(value.get("boolean")) is not bool:
        raise MobileMediaServiceUnavailableError(
            "GraphDB returned an invalid ASK result."
        )
    return value["boolean"]


def _receipt_query(commit: MobileMediaCommit) -> str:
    receipt = URIRef(commit.receipt_iri).n3()
    upload_id = Literal(commit.upload_id).n3()
    client_asset_id = Literal(commit.client_asset_id).n3()
    event_id = Literal(commit.event_id).n3()
    return f"""
SELECT ?receipt ?eventId ?requestDigest ?owner ?stagingArea ?resource ?result
WHERE {{
  GRAPH {RECEIPT_GRAPH.n3()} {{
    ?receipt {RDF.type.n3()} {RECEIPT_CLASS.n3()} .
    OPTIONAL {{ ?receipt {UPLOAD_ID.n3()} ?storedUploadId . }}
    OPTIONAL {{ ?receipt {CLIENT_ASSET_ID.n3()} ?storedClientAssetId . }}
    OPTIONAL {{ ?receipt {EVENT_ID.n3()} ?eventId . }}
    OPTIONAL {{ ?receipt {REQUEST_DIGEST.n3()} ?requestDigest . }}
    OPTIONAL {{ ?receipt {OWNER.n3()} ?owner . }}
    OPTIONAL {{ ?receipt {STAGING_AREA.n3()} ?stagingArea . }}
    OPTIONAL {{ ?receipt {RESOURCE.n3()} ?resource . }}
    OPTIONAL {{ ?receipt {RESULT.n3()} ?result . }}
    FILTER(
      ?receipt = {receipt} ||
      ?storedUploadId = {upload_id} ||
      ?storedClientAssetId = {client_asset_id} ||
      ?eventId = {event_id}
    )
  }}
}}
LIMIT 2
"""


def _target_query(commit: MobileMediaCommit) -> str:
    owner = URIRef(commit.owner_user_iri).n3()
    area = URIRef(commit.staging_area_id).n3()
    return f"""
PREFIX oldap: <http://oldap.org/base#>
PREFIX shared: <http://oldap.org/shared#>
PREFIX fasnacht: <http://oldap.org/fasnacht#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?dataGraph ?project ?projectShortName ?defaultRole ?mediaPath
WHERE {{
  GRAPH ?dataGraph {{
    {area} a ?areaClass ;
      shared:mediaPath ?mediaPath ;
      shared:stagingDefaultRole ?defaultRole ;
      fasnacht:depositingOrganisation ?organisation ;
      oldap:attachedToRole ?defaultRole .
    << {area} oldap:attachedToRole ?defaultRole >>
      oldap:hasDataPermission ?areaPermission .
    ?organisation a fasnacht:Organisation .
  }}
  FILTER(
    ?areaClass = shared:StagingArea ||
    EXISTS {{ GRAPH ?areaOntology {{
      ?areaClass rdfs:subClassOf+ shared:StagingArea .
    }} }}
  )
  GRAPH oldap:admin {{
    ?project a oldap:Project ;
      oldap:projectShortName ?projectShortName ;
      oldap:namespaceIri ?namespaceIri .
    {owner} a oldap:User, fasnacht:FasnachtUser ;
      oldap:isActive true ;
      fasnacht:memberOfOrganisation ?organisation ;
      oldap:hasRole ?defaultRole .
    ?areaPermission oldap:permissionValue ?areaPermissionValue .
    FILTER(xsd:integer(?areaPermissionValue) >= 2)
  }}
  FILTER(?dataGraph = IRI(CONCAT(STR(?namespaceIri), "data")))
}}
LIMIT 2
"""


def _admin_create_query(commit: MobileMediaCommit, project_iri: str) -> str:
    owner = URIRef(commit.owner_user_iri).n3()
    project = URIRef(project_iri).n3()
    return f"""
PREFIX oldap: <http://oldap.org/base#>
ASK {{ GRAPH oldap:admin {{
  {{
    << {owner} oldap:inProject {project} >>
      oldap:hasAdminPermission oldap:ADMIN_CREATE .
  }} UNION {{
    << {owner} oldap:inProject ?anyProject >>
      oldap:hasAdminPermission oldap:ADMIN_OLDAP .
  }}
}} }}
"""


def _inbox_query(commit: MobileMediaCommit, target: MobileMediaTarget) -> str:
    graph = URIRef(target.data_graph_iri).n3()
    area = URIRef(commit.staging_area_id).n3()
    return f"""
PREFIX oldap: <http://oldap.org/base#>
PREFIX shared: <http://oldap.org/shared#>
PREFIX schema: <https://schema.org/>
SELECT ?top ?mobile ?mobileRole ?mobilePermission
WHERE {{
  GRAPH {graph} {{
    ?top a shared:StagingFolder ;
      schema:name ?topName ;
      shared:inStagingArea {area} .
    FILTER(STR(?topName) = "top")
    FILTER NOT EXISTS {{ ?top shared:inStagingFolder ?parent . }}
    OPTIONAL {{
      ?mobile a shared:StagingFolder ;
        schema:name ?mobileName ;
        shared:inStagingArea {area} ;
        shared:inStagingFolder ?top .
      FILTER(STR(?mobileName) = "Mobile")
      OPTIONAL {{
        ?mobile oldap:attachedToRole ?mobileRole .
        OPTIONAL {{
          << ?mobile oldap:attachedToRole ?mobileRole >>
            oldap:hasDataPermission ?mobilePermission .
        }}
      }}
    }}
  }}
}}
LIMIT 3
"""


def _resource_collision_query(commit: MobileMediaCommit) -> str:
    resource = URIRef(commit.resource_iri).n3()
    asset = Literal(commit.client_asset_id).n3()
    return f"""
PREFIX shared: <http://oldap.org/shared#>
ASK {{
  GRAPH ?graph {{
    {{ {resource} ?property ?value . }}
    UNION
    {{ ?existing shared:assetId {asset} . }}
  }}
}}
"""


def _atomic_insert(
    commit: MobileMediaCommit,
    result: MobileMediaCommitResult,
    target: MobileMediaTarget,
    *,
    media_base_url: str,
) -> str:
    graph = URIRef(target.data_graph_iri).n3()
    resource = URIRef(commit.resource_iri).n3()
    owner = URIRef(commit.owner_user_iri).n3()
    area = URIRef(commit.staging_area_id).n3()
    folder = URIRef(target.mobile_folder_iri).n3()
    role = URIRef(target.default_role_iri).n3()
    receipt = URIRef(commit.receipt_iri).n3()
    timestamp = Literal(result.committed_at, datatype=XSD.dateTimeStamp).n3()
    server_url = Literal(f"{media_base_url}/iiif/3/", datatype=XSD.anyURI).n3()
    result_json = Literal(rfc8785.dumps(result.to_dict()).decode("utf-8")).n3()
    comment = (
        f" ;\n      schema:comment {Literal(commit.comment, lang='en').n3()}"
        if commit.comment is not None
        else ""
    )
    return f"""
PREFIX oldap: <http://oldap.org/base#>
PREFIX shared: <http://oldap.org/shared#>
PREFIX schema: <https://schema.org/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX dcmitype: <http://purl.org/dc/dcmitype/>
INSERT DATA {{
  GRAPH {graph} {{
    {resource} a shared:StagingMediaObject ;
      dcterms:type dcmitype:StillImage ;
      shared:mediaAccessMode "local" ;
      shared:originalName {Literal(commit.original_name).n3()} ;
      shared:originalMimeType {Literal(commit.original_mime_type).n3()} ;
      shared:checksum {Literal(commit.checksum_sha256).n3()} ;
      shared:assetId {Literal(commit.client_asset_id).n3()} ;
      shared:protocol "iiif" ;
      shared:serverUrl {server_url} ;
      shared:derivativeName "master.tif" ;
      shared:path {Literal(target.storage_path).n3()} ;
      shared:inStagingArea {area} ;
      shared:inStagingFolder {folder} ;
      shared:stagingStatus shared:StagingStatusNew ;
      oldap:createdBy {owner} ;
      oldap:creationDate {timestamp} ;
      oldap:lastModifiedBy {owner} ;
      oldap:lastModificationDate {timestamp} ;
      oldap:attachedToRole {role}{comment} .
    << {resource} oldap:attachedToRole {role} >>
      oldap:hasDataPermission oldap:DATA_DELETE .
  }}
  GRAPH {RECEIPT_GRAPH.n3()} {{
    {receipt} a {RECEIPT_CLASS.n3()} ;
      {UPLOAD_ID.n3()} {Literal(commit.upload_id).n3()} ;
      {CLIENT_ASSET_ID.n3()} {Literal(commit.client_asset_id).n3()} ;
      {EVENT_ID.n3()} {Literal(commit.event_id).n3()} ;
      {REQUEST_DIGEST.n3()} {Literal(commit.request_digest).n3()} ;
      {OWNER.n3()} {owner} ;
      {STAGING_AREA.n3()} {area} ;
      {RESOURCE.n3()} {resource} ;
      {RESULT.n3()} {result_json} .
  }}
}}
"""
