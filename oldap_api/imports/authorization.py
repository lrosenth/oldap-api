"""OLDAP permission and staging-target checks for ZIP import jobs."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Any, Protocol

from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.project import Project
from rdflib import URIRef

from .domain import TargetSnapshot


class ImportPermissionDeniedError(PermissionError):
    """Raised when a user lacks one of the two required permissions."""

    code = "IMPORT_PERMISSION_DENIED"


class ImportTargetNotFoundError(LookupError):
    """Raised when the staging area/folder pair is absent or inconsistent."""

    code = "IMPORT_TARGET_NOT_FOUND"


class ImportQuotaNotConfiguredError(RuntimeError):
    """Raised when a staging area has no explicit extracted-byte quota."""

    code = "IMPORT_QUOTA_NOT_CONFIGURED"


@dataclass(frozen=True, slots=True)
class AuthorizedTarget:
    """Validated immutable target snapshot and its current quota ceiling."""

    snapshot: TargetSnapshot
    quota_limit_bytes: int


@dataclass(frozen=True, slots=True)
class TargetChild:
    """One named direct child relevant to import collision detection."""

    kind: str
    name: str


@dataclass(frozen=True, slots=True)
class TargetInspection:
    """Current target identity plus its bounded direct-child inventory."""

    snapshot: TargetSnapshot
    children: tuple[TargetChild, ...]


class ImportAuthorizer(Protocol):
    """Resolve and authorize a selected staging target for one user."""

    def authorize_target(
        self,
        connection: Any,
        *,
        project_short_name: str,
        staging_area_iri: str,
        target_root_folder_iri: str,
    ) -> AuthorizedTarget: ...


class ImportTargetInspector(Protocol):
    """Read current target identity and direct children for a leased job."""

    def inspect_target(self, target: TargetSnapshot) -> TargetInspection: ...


class OldapImportAuthorizer:
    """Perform ADMIN_CREATE, DATA_UPDATE, type, membership, and quota checks."""

    def authorize_target(
        self,
        connection: Any,
        *,
        project_short_name: str,
        staging_area_iri: str,
        target_root_folder_iri: str,
    ) -> AuthorizedTarget:
        project = Project.read(
            con=connection,
            projectIri_SName=project_short_name,
            ignore_cache=True,
        )
        if not _has_admin_create(connection.userdata, str(project.projectIri)):
            raise ImportPermissionDeniedError(
                "ADMIN_CREATE is required for the selected project."
            )

        query = _target_query(
            connection.userIri.toRdf,
            _project_data_graph_iri(project),
            staging_area_iri,
            target_root_folder_iri,
        )
        rows = connection.query(query).get("results", {}).get("bindings", [])
        if not rows:
            raise ImportTargetNotFoundError(
                "The staging area and target folder do not form an authorized target."
            )
        row = rows[0]
        if "quota" not in row:
            raise ImportQuotaNotConfiguredError(
                "The staging area has no shared:stagingQuotaBytes value."
            )
        quota = int(row["quota"]["value"])
        if quota <= 0:
            raise ImportQuotaNotConfiguredError(
                "The staging-area quota must be greater than zero."
            )
        return AuthorizedTarget(
            snapshot=TargetSnapshot(
                project_short_name=project_short_name,
                staging_area_iri=staging_area_iri,
                staging_area_name=row["areaName"]["value"],
                target_root_folder_iri=target_root_folder_iri,
                target_root_folder_name=row["folderName"]["value"],
            ),
            quota_limit_bytes=quota,
        )


class OldapImportTargetInspector:
    """Read a bounded target inventory through the import service connection."""

    MAX_DIRECT_CHILDREN = 10_000

    def __init__(
        self,
        connection: Any,
        *,
        data_graph_resolver: Callable[[Any, str], URIRef] | None = None,
    ) -> None:
        self._connection = connection
        self._data_graph_resolver = (
            data_graph_resolver or resolve_project_data_graph_iri
        )

    def inspect_target(self, target: TargetSnapshot) -> TargetInspection:
        """Return the current target snapshot and named direct children.

        Raises:
            ImportTargetNotFoundError: If the selected folder no longer belongs
                to the recorded staging area.
            RuntimeError: If the direct-child inventory exceeds the bounded MVP
                query envelope.
        """

        data_graph_iri = self._data_graph_resolver(
            self._connection, target.project_short_name
        )
        rows = (
            self._connection.query(_target_inventory_query(target, data_graph_iri))
            .get("results", {})
            .get("bindings", [])
        )
        if not rows:
            raise ImportTargetNotFoundError(
                "The selected staging target no longer exists."
            )
        first = rows[0]
        current = TargetSnapshot(
            project_short_name=target.project_short_name,
            staging_area_iri=target.staging_area_iri,
            staging_area_name=first["areaName"]["value"],
            target_root_folder_iri=target.target_root_folder_iri,
            target_root_folder_name=first["folderName"]["value"],
        )
        children = tuple(
            TargetChild(
                kind=(
                    "folder"
                    if row["kind"]["value"] == "http://oldap.org/shared#StagingFolder"
                    else "media"
                ),
                name=row["name"]["value"],
            )
            for row in rows
            if {"child", "kind", "name"} <= set(row)
        )
        if len(children) > self.MAX_DIRECT_CHILDREN:
            raise RuntimeError("The target contains too many direct children.")
        return TargetInspection(snapshot=current, children=children)


def _has_admin_create(userdata: Any, project_iri: str) -> bool:
    if userdata is None:
        return False
    for project, permissions in userdata.inProject.items():
        permission_set = set(permissions or ())
        if AdminPermission.ADMIN_OLDAP in permission_set:
            return True
        if (
            str(project) == project_iri
            and AdminPermission.ADMIN_CREATE in permission_set
        ):
            return True
    return False


def resolve_project_data_graph_iri(connection: Any, project_short_name: str) -> URIRef:
    """Resolve one project's absolute data-graph IRI from OLDAP metadata.

    Custom import SPARQL is intentionally self-contained and never relies on a
    process-local QName context. This matters for access-token connections,
    which do not populate project prefixes before returning from construction.

    Args:
        connection: Authenticated OLDAP connection used to read the project.
        project_short_name: Validated project short name.

    Returns:
        Absolute named-graph IRI formed from the project's namespace and the
        conventional ``data`` suffix.
    """

    project = Project.read(
        con=connection,
        projectIri_SName=project_short_name,
        ignore_cache=True,
    )
    return _project_data_graph_iri(project)


def _project_data_graph_iri(project: Project) -> URIRef:
    """Return the conventional absolute data graph for a loaded project."""

    return URIRef(f"{project.namespaceIri}data")


def _target_query(
    user_iri_rdf: str,
    data_graph_iri: URIRef,
    staging_area_iri: str,
    target_root_folder_iri: str,
) -> str:
    """Build the bounded target and effective-role authorization query."""
    area = URIRef(staging_area_iri).n3()
    folder = URIRef(target_root_folder_iri).n3()
    data_graph = data_graph_iri.n3()
    return f"""
PREFIX oldap: <http://oldap.org/base#>
PREFIX shared: <http://oldap.org/shared#>
PREFIX schema: <https://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?areaName ?folderName ?quota
WHERE {{
  GRAPH {data_graph} {{
    {area} a ?areaClass ;
      schema:name ?areaName ;
      oldap:attachedToRole ?role .
    OPTIONAL {{ {area} shared:stagingQuotaBytes ?quota . }}
    << {area} oldap:attachedToRole ?role >>
      oldap:hasDataPermission ?dataPermission .
    {folder} a shared:StagingFolder ;
      shared:inStagingArea {area} ;
      schema:name ?folderName .
  }}
  FILTER(
    ?areaClass = shared:StagingArea ||
    EXISTS {{ GRAPH ?areaOntology {{
      ?areaClass rdfs:subClassOf+ shared:StagingArea .
    }} }}
  )
  GRAPH oldap:admin {{
    {user_iri_rdf} oldap:hasRole ?role .
    ?dataPermission oldap:permissionValue ?permissionValue .
    FILTER(?permissionValue >= 4)
  }}
}}
LIMIT 1
"""


def _target_inventory_query(target: TargetSnapshot, data_graph_iri: URIRef) -> str:
    """Build the bounded service-side direct-child inventory query."""

    area = URIRef(target.staging_area_iri).n3()
    folder = URIRef(target.target_root_folder_iri).n3()
    data_graph = data_graph_iri.n3()
    limit = OldapImportTargetInspector.MAX_DIRECT_CHILDREN + 2
    return f"""
PREFIX shared: <http://oldap.org/shared#>
PREFIX schema: <https://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?areaName ?folderName ?child ?kind ?name
WHERE {{
  GRAPH {data_graph} {{
    {area} a ?areaClass ;
      schema:name ?areaName .
    {folder} a shared:StagingFolder ;
      shared:inStagingArea {area} ;
      schema:name ?folderName .
    OPTIONAL {{
      ?child shared:inStagingFolder {folder} ;
        shared:inStagingArea {area} ;
        a ?kind .
      VALUES ?kind {{ shared:StagingFolder shared:StagingMediaObject }}
      OPTIONAL {{ ?child schema:name ?schemaName . }}
      OPTIONAL {{ ?child shared:originalName ?originalName . }}
      BIND(COALESCE(?originalName, ?schemaName) AS ?name)
    }}
  }}
  FILTER(
    ?areaClass = shared:StagingArea ||
    EXISTS {{ GRAPH ?areaOntology {{
      ?areaClass rdfs:subClassOf+ shared:StagingArea .
    }} }}
  )
}}
LIMIT {limit}
"""
