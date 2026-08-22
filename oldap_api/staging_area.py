"""Protected Staging system-folder policy and atomic empty-area deletion."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorValue
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from oldap_api.staging_lock import (
    RedisStagingMutationLock,
    StagingMutationLockUnavailable,
)

STAGING_FOLDER_CLASS = "http://oldap.org/shared#StagingFolder"
SYSTEM_FOLDER_NAMES = {
    "top": "top",
    "mobile": "Mobile",
    "trash": "Trash",
}
STAGING_MUTATION_CLASSES = {
    "shared:StagingArea",
    "http://oldap.org/shared#StagingArea",
    "fasnacht:StagingArea",
    "http://oldap.org/fasnacht#StagingArea",
    "shared:StagingFolder",
    STAGING_FOLDER_CLASS,
    "shared:StagingMediaObject",
    "http://oldap.org/shared#StagingMediaObject",
}
T = TypeVar("T")


class StagingStructureError(Exception):
    """Base error for protected Staging structure operations."""

    status = 409


class StagingStructureConflict(StagingStructureError):
    """Raised when a generic operation would violate system-folder policy."""


class StagingAreaValidationError(StagingStructureError):
    """Raised when a caller supplies an invalid StagingArea identifier."""

    status = 400


class StagingAreaNotFound(StagingStructureError):
    """Raised when the requested StagingArea is absent from the project graph."""

    status = 404


class StagingAreaPermissionDenied(StagingStructureError):
    """Raised when the current user cannot delete every managed resource."""

    status = 403


class StagingAreaServiceUnavailable(StagingStructureError):
    """Raised when GraphDB returns an unusable result or transaction failure."""

    status = 503


class QueryConnection(Protocol):
    """Minimal connection surface used by generic-operation policy checks."""

    context_name: str

    def query(self, query: str) -> Any: ...


class TransactionalConnection(QueryConnection, Protocol):
    """Minimal oldaplib transaction surface used by atomic area deletion."""

    userIri: Any

    def transaction_start(self) -> None: ...

    def transaction_query(self, query: str) -> Any: ...

    def transaction_update(self, query: str) -> None: ...

    def transaction_commit(self) -> None: ...

    def transaction_abort(self) -> None: ...


@dataclass(frozen=True, slots=True)
class StagingGraph:
    """Validated project identifiers required by Staging structure queries."""

    project_short_name: str
    project_namespace: str
    data_graph_iri: str

    @classmethod
    def resolve(cls, connection: QueryConnection, project: str) -> "StagingGraph":
        """Resolve a project prefix to its authoritative data graph IRI."""

        try:
            project_short_name = str(Xsd_NCName(project, validate=True))
            namespace = Context(name=connection.context_name).get(project_short_name)
        except (OldapError, OldapErrorValue, ValueError) as error:
            raise StagingAreaNotFound("The project does not exist.") from error
        if namespace is None:
            try:
                rows = _bindings(
                    connection.query(_project_namespace_query(project_short_name))
                )
            except StagingStructureError:
                raise
            except OldapError as error:
                raise StagingAreaServiceUnavailable(
                    "The project namespace could not be resolved."
                ) from error
            namespaces = _values(rows, "namespace")
            if not rows:
                raise StagingAreaNotFound("The project does not exist.")
            if len(namespaces) != 1:
                raise StagingAreaServiceUnavailable(
                    "The project namespace configuration is ambiguous."
                )
            project_namespace = next(iter(namespaces))
        else:
            project_namespace = str(namespace)
        try:
            namespace_iri = Iri(project_namespace, validate=True)
        except OldapErrorValue as error:
            raise StagingAreaServiceUnavailable(
                "The project namespace configuration is invalid."
            ) from error
        if ":" not in str(namespace_iri):
            raise StagingAreaServiceUnavailable(
                "The project namespace configuration is invalid."
            )
        return cls(
            project_short_name=project_short_name,
            project_namespace=str(namespace_iri),
            data_graph_iri=f"{namespace_iri}data",
        )


class StagingSystemFolderPolicy:
    """Guard the exact ``top`` / ``Mobile`` / ``Trash`` system structure."""

    def __init__(self, connection: QueryConnection, project: str) -> None:
        self._connection = connection
        self._graph = StagingGraph.resolve(connection, project)

    def assert_create_allowed(self, resource_class: str, data: Any) -> None:
        """Reject reserved-name ambiguity, duplicates, and Mobile children."""

        if not _is_staging_folder_class(resource_class):
            return
        if not isinstance(data, dict):
            return

        name = _single_text(data.get("schema:name"))
        area = _single_iri(data.get("shared:inStagingArea"))
        parent = _single_iri(data.get("shared:inStagingFolder"), required=False)
        if not name or not area:
            return

        state = self._system_state(area)
        reserved_kind = _reserved_kind(name)
        if reserved_kind is None:
            if parent is not None and parent in state.mobile:
                raise StagingStructureConflict(
                    "The protected Mobile inbox cannot contain child folders."
                )
            return
        if name != SYSTEM_FOLDER_NAMES[reserved_kind]:
            raise StagingStructureConflict(
                f'The reserved folder name must use the exact spelling "{SYSTEM_FOLDER_NAMES[reserved_kind]}".'
            )

        if reserved_kind == "top":
            if parent is not None or state.top:
                raise StagingStructureConflict(
                    "The StagingArea already has a root top folder or the reserved name is misplaced."
                )
            return

        if len(state.top) != 1 or parent not in state.top:
            raise StagingStructureConflict(
                f'The reserved folder "{SYSTEM_FOLDER_NAMES[reserved_kind]}" must be a direct child of top.'
            )
        existing = state.mobile if reserved_kind == "mobile" else state.trash
        if existing:
            raise StagingStructureConflict(
                f'The StagingArea already has a "{SYSTEM_FOLDER_NAMES[reserved_kind]}" system folder.'
            )
        if reserved_kind == "mobile":
            roles = data.get("attachedToRole", data.get("oldap:attachedToRole"))
            if not _has_exact_mobile_policy(
                roles,
                state.default_role,
                Context(name=self._connection.context_name),
            ):
                raise StagingStructureConflict(
                    "The Mobile inbox must grant only DATA_VIEW to the StagingArea default role."
                )

    def assert_update_allowed(self, folder_iri: str, data: Any) -> None:
        """Reject every generic mutation of protected system folders."""

        if not isinstance(data, dict):
            return
        name = _single_text(data.get("schema:name"))
        if name is not None and _reserved_kind(name) is not None:
            raise StagingStructureConflict(
                "Reserved Staging system-folder names cannot be assigned through a generic update."
            )
        if self._is_protected(folder_iri):
            raise StagingStructureConflict(
                "Protected Staging system folders cannot be changed through the generic API."
            )

    def assert_move_allowed(self, folder_iri: str, target_iri: str) -> None:
        """Reject moves of protected folders and moves into Mobile."""

        if self._is_protected(folder_iri):
            raise StagingStructureConflict(
                "Protected Staging system folders cannot be moved."
            )
        if self._is_mobile(target_iri):
            raise StagingStructureConflict(
                "The protected Mobile inbox cannot contain child folders."
            )

    def assert_delete_allowed(self, folder_iri: str) -> None:
        """Reject generic deletion of every managed system folder."""

        if self._is_protected(folder_iri):
            raise StagingStructureConflict(
                "Protected Staging system folders cannot be deleted through the generic API."
            )

    def assert_staging_area_delete_allowed(self, resource_class: Any) -> None:
        """Require every StagingArea deletion to use the atomic dedicated route."""

        if _is_staging_area_class(resource_class):
            raise StagingStructureConflict(
                "StagingAreas must be deleted through the atomic empty-area operation."
            )

    def assert_transform_allowed(self, folder_iri: str) -> None:
        """Reject reclassification of every protected system-folder resource."""

        if self._is_protected(folder_iri):
            raise StagingStructureConflict(
                "Protected Staging system folders cannot be transformed."
            )

    def assert_staging_area_transform_allowed(self, resource_class: Any) -> None:
        """Reject generic reclassification of a managed StagingArea."""

        if _is_staging_area_class(resource_class):
            raise StagingStructureConflict(
                "StagingAreas cannot be transformed through the generic API."
            )

    def assert_transform_target_allowed(self, target_class: str) -> None:
        """Reject generic transformation into managed Staging structure classes."""

        if is_staging_structure_class(target_class):
            raise StagingStructureConflict(
                "StagingAreas and folders must be created through validated create operations."
            )

    def _is_protected(self, folder_iri: str) -> bool:
        return _ask(
            self._connection.query(_protected_folder_query(self._graph, folder_iri))
        )

    def _is_mobile(self, folder_iri: str) -> bool:
        return _ask(
            self._connection.query(_mobile_folder_query(self._graph, folder_iri))
        )

    def _system_state(self, staging_area_iri: str) -> "SystemFolderState":
        rows = _bindings(
            self._connection.query(_system_state_query(self._graph, staging_area_iri))
        )
        if not rows:
            raise StagingStructureConflict("The StagingArea does not exist.")
        default_roles = _values(rows, "defaultRole")
        if len(default_roles) != 1:
            raise StagingStructureConflict(
                "The StagingArea default-role configuration is ambiguous."
            )
        folders: dict[str, tuple[str, str | None]] = {}
        for row in rows:
            folder_entry = row.get("reservedFolder")
            if folder_entry is None:
                continue
            try:
                folder = folder_entry["value"]
                name = row["reservedName"]["value"]
                parent = row.get("reservedParent", {}).get("value")
            except (KeyError, TypeError) as error:
                raise StagingAreaServiceUnavailable(
                    "GraphDB returned an invalid StagingArea structure."
                ) from error
            current = folders.setdefault(folder, (name, parent))
            if current != (name, parent):
                raise StagingStructureConflict(
                    "The StagingArea system-folder structure is ambiguous."
                )

        by_kind: dict[str, set[str]] = {kind: set() for kind in SYSTEM_FOLDER_NAMES}
        for folder, (name, parent) in folders.items():
            kind = _reserved_kind(name)
            if kind is None or name != SYSTEM_FOLDER_NAMES[kind]:
                raise StagingStructureConflict(
                    "The StagingArea contains a reserved folder name with invalid spelling."
                )
            if kind == "top" and parent is not None:
                raise StagingStructureConflict(
                    "The reserved top folder must be the StagingArea root."
                )
            by_kind[kind].add(folder)

        if any(len(values) > 1 for values in by_kind.values()):
            raise StagingStructureConflict(
                "The StagingArea contains duplicate reserved system folders."
            )
        top = frozenset(by_kind["top"])
        for kind in ("mobile", "trash"):
            for folder in by_kind[kind]:
                if len(top) != 1 or folders[folder][1] not in top:
                    raise StagingStructureConflict(
                        f'The reserved folder "{SYSTEM_FOLDER_NAMES[kind]}" must be a direct child of top.'
                    )

        return SystemFolderState(
            default_role=next(iter(default_roles)),
            top=top,
            mobile=frozenset(by_kind["mobile"]),
            trash=frozenset(by_kind["trash"]),
        )


@dataclass(frozen=True, slots=True)
class SystemFolderState:
    """Current exact system-folder identities for one StagingArea."""

    default_role: str
    top: frozenset[str]
    mobile: frozenset[str]
    trash: frozenset[str]


@dataclass(frozen=True, slots=True)
class DeletionTarget:
    """Validated four-resource StagingArea teardown target."""

    area: str
    top: str
    mobile: str
    trash: str

    @property
    def resources(self) -> tuple[str, str, str, str]:
        return self.area, self.top, self.mobile, self.trash


class GraphDbStagingAreaRepository:
    """Delete an empty system-folder-only StagingArea in one transaction."""

    def __init__(self, connection: TransactionalConnection, project: str) -> None:
        self._connection = connection
        self._graph = StagingGraph.resolve(connection, project)

    def delete_empty(self, staging_area_iri: str) -> DeletionTarget:
        """Validate permissions and contents, then atomically delete four resources."""

        area = _validated_request_iri(staging_area_iri)
        actor = _validated_absolute_iri(str(self._connection.userIri))
        self._connection.transaction_start()
        try:
            target = self._resolve_target(area)
            if not self._can_delete(actor, target):
                raise StagingAreaPermissionDenied(
                    "The current user cannot delete the complete StagingArea."
                )
            if _ask(
                self._connection.transaction_query(
                    _staging_contents_query(self._graph, target)
                )
            ):
                raise StagingStructureConflict(
                    "The StagingArea contains media or user folders and cannot be deleted."
                )
            if _ask(
                self._connection.transaction_query(
                    _external_references_query(self._graph, target)
                )
            ):
                raise StagingStructureConflict(
                    "The StagingArea system resources are still referenced."
                )
            self._connection.transaction_update(_atomic_delete(self._graph, target))
            if _ask(
                self._connection.transaction_query(
                    _remaining_targets_query(self._graph, target)
                )
            ):
                raise StagingAreaServiceUnavailable(
                    "The StagingArea deletion did not remove every managed resource."
                )
            self._connection.transaction_commit()
            return target
        except Exception:
            self._connection.transaction_abort()
            raise

    def _resolve_target(self, area: str) -> DeletionTarget:
        rows = _bindings(
            self._connection.transaction_query(
                _deletion_target_query(self._graph, area)
            )
        )
        if not rows:
            if _ask(
                self._connection.transaction_query(
                    _staging_area_exists_query(self._graph, area)
                )
            ):
                raise StagingStructureConflict(
                    "The StagingArea has no complete system-folder structure."
                )
            raise StagingAreaNotFound("The StagingArea does not exist.")

        folders: dict[str, tuple[str, str | None]] = {}
        for row in rows:
            try:
                folder = row["folder"]["value"]
                name = row["name"]["value"]
                parent = row.get("parent", {}).get("value")
            except (KeyError, TypeError) as error:
                raise StagingAreaServiceUnavailable(
                    "GraphDB returned an invalid StagingArea structure."
                ) from error
            current = folders.setdefault(folder, (name, parent))
            if current != (name, parent):
                raise StagingStructureConflict(
                    "The StagingArea system-folder structure is ambiguous."
                )

        roots = [
            iri
            for iri, (name, parent) in folders.items()
            if name == "top" and parent is None
        ]
        if len(roots) != 1:
            raise StagingStructureConflict(
                "The StagingArea must contain exactly one root top folder."
            )
        top = roots[0]
        mobile = [
            iri
            for iri, (name, parent) in folders.items()
            if name == "Mobile" and parent == top
        ]
        trash = [
            iri
            for iri, (name, parent) in folders.items()
            if name == "Trash" and parent == top
        ]
        if len(mobile) != 1 or len(trash) != 1 or len(folders) != 3:
            raise StagingStructureConflict(
                "The StagingArea must contain only one exact top, Mobile, and Trash system-folder set."
            )
        return DeletionTarget(area=area, top=top, mobile=mobile[0], trash=trash[0])

    def _can_delete(self, actor: str, target: DeletionTarget) -> bool:
        if _ask(
            self._connection.transaction_query(_admin_delete_query(self._graph, actor))
        ):
            return True
        rows = _bindings(
            self._connection.transaction_query(
                _resource_delete_permissions_query(self._graph, actor, target)
            )
        )
        return _values(rows, "resource") == frozenset(target.resources)


def run_staging_mutation(resource_classes: Any, operation: Callable[[], T]) -> T:
    """Serialize one affected generic or dedicated Staging write."""

    values = (
        resource_classes
        if isinstance(resource_classes, (list, tuple, set, frozenset))
        else (resource_classes,)
    )
    if not any(is_staging_mutation_class(value) for value in values):
        return operation()
    try:
        return RedisStagingMutationLock().run(operation)
    except StagingMutationLockUnavailable as error:
        raise StagingAreaServiceUnavailable(str(error)) from error


def _is_staging_folder_class(value: str) -> bool:
    return value in {"shared:StagingFolder", STAGING_FOLDER_CLASS}


def is_staging_folder_class(value: Any) -> bool:
    """Return whether a class is the managed StagingFolder class."""

    return _is_staging_folder_class(str(value))


def is_staging_mutation_class(value: Any) -> bool:
    """Return whether writes of this class require the shared Staging lease."""

    return str(value) in STAGING_MUTATION_CLASSES


def _is_staging_area_class(value: Any) -> bool:
    return str(value) in {
        "shared:StagingArea",
        "http://oldap.org/shared#StagingArea",
        "fasnacht:StagingArea",
        "http://oldap.org/fasnacht#StagingArea",
    }


def is_staging_structure_class(value: Any) -> bool:
    """Return whether a class belongs to the protected Staging structure."""

    return _is_staging_folder_class(str(value)) or _is_staging_area_class(value)


def _single_text(value: Any) -> str | None:
    if isinstance(value, list):
        if len(value) != 1:
            return None
        value = value[0]
    if not isinstance(value, str) or not value.strip():
        return None
    lexical = value.strip()
    suffix = lexical.rsplit("@", 1)
    if len(suffix) == 2 and len(suffix[1]) in {2, 3} and suffix[1].isalpha():
        lexical = suffix[0]
    return lexical.strip()


def _single_iri(value: Any, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if isinstance(value, list):
        if len(value) != 1:
            return None
        value = value[0]
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return str(Iri(value.strip(), validate=True))
    except OldapErrorValue:
        return None


def _reserved_kind(name: str) -> str | None:
    normalized = name.casefold()
    for kind, reserved in SYSTEM_FOLDER_NAMES.items():
        if normalized == reserved.casefold():
            return kind
    return None


def _expanded_iri(value: str, context: Context) -> str | None:
    try:
        if "://" in value or value.startswith("urn:"):
            return _validated_absolute_iri(value)
        return str(context.qname2iri(value, validate=True))
    except (OldapError, OldapErrorValue, ValueError):
        return None


def _has_exact_mobile_policy(roles: Any, default_role: str, context: Context) -> bool:
    if not isinstance(roles, dict) or len(roles) != 1:
        return False
    role, permission = next(iter(roles.items()))
    if not isinstance(role, str) or not isinstance(permission, str):
        return False
    return (
        _expanded_iri(role, context) == default_role
        and permission.removeprefix("oldap:") == "DATA_VIEW"
    )


def _validated_absolute_iri(value: str) -> str:
    try:
        iri = Iri(value, validate=True)
    except OldapErrorValue as error:
        raise StagingStructureConflict(
            "The supplied resource IRI is invalid."
        ) from error
    if ":" not in str(iri):
        raise StagingStructureConflict("The supplied resource IRI is invalid.")
    return str(iri)


def _validated_request_iri(value: str) -> str:
    """Validate one client-owned IRI while preserving the HTTP 400 contract."""

    try:
        return _validated_absolute_iri(value)
    except StagingStructureConflict as error:
        raise StagingAreaValidationError(str(error)) from error


def _bindings(value: Any) -> list[dict[str, Any]]:
    try:
        bindings = value["results"]["bindings"]
    except (KeyError, TypeError) as error:
        raise StagingAreaServiceUnavailable(
            "GraphDB returned an invalid query result."
        ) from error
    if not isinstance(bindings, list) or not all(
        isinstance(row, dict) for row in bindings
    ):
        raise StagingAreaServiceUnavailable("GraphDB returned an invalid query result.")
    return bindings


def _ask(value: Any) -> bool:
    if not isinstance(value, dict) or type(value.get("boolean")) is not bool:
        raise StagingAreaServiceUnavailable("GraphDB returned an invalid ASK result.")
    return value["boolean"]


def _values(rows: list[dict[str, Any]], key: str) -> frozenset[str]:
    values: set[str] = set()
    for row in rows:
        entry = row.get(key)
        if entry is None:
            continue
        if not isinstance(entry, dict) or not isinstance(entry.get("value"), str):
            raise StagingAreaServiceUnavailable("GraphDB returned an invalid binding.")
        values.add(entry["value"])
    return frozenset(values)


def _graph_term(graph: StagingGraph) -> str:
    return URIRef(graph.data_graph_iri).n3()


def _iri_term(value: str) -> str:
    return URIRef(_validated_absolute_iri(value)).n3()


def _system_state_query(graph: StagingGraph, area: str) -> str:
    return f"""# staging-system-state
PREFIX oldap: <http://oldap.org/base#>
PREFIX shared: <http://oldap.org/shared#>
PREFIX schema: <https://schema.org/>
SELECT ?defaultRole ?reservedFolder ?reservedName ?reservedParent WHERE {{
  GRAPH {_graph_term(graph)} {{
    {_iri_term(area)} shared:stagingDefaultRole ?defaultRole .
    OPTIONAL {{
      ?reservedFolder a shared:StagingFolder ;
        schema:name ?reservedName ;
        shared:inStagingArea {_iri_term(area)} .
      FILTER(LCASE(STR(?reservedName)) IN ("top", "mobile", "trash"))
      OPTIONAL {{ ?reservedFolder shared:inStagingFolder ?reservedParent . }}
    }}
  }}
}}
"""


def _project_namespace_query(project_short_name: str) -> str:
    return f"""# staging-project-namespace
PREFIX oldap: <http://oldap.org/base#>
SELECT ?namespace WHERE {{ GRAPH oldap:admin {{
  ?project a oldap:Project ;
    oldap:projectShortName {Literal(project_short_name, datatype=XSD.NCName).n3()} ;
    oldap:namespaceIri ?namespace .
}} }}
LIMIT 2
"""


def _protected_folder_query(graph: StagingGraph, folder: str) -> str:
    folder_term = _iri_term(folder)
    return f"""# protected-staging-folder
PREFIX shared: <http://oldap.org/shared#>
PREFIX schema: <https://schema.org/>
ASK {{ GRAPH {_graph_term(graph)} {{
  {{
    {folder_term} a shared:StagingFolder ; schema:name ?name ; shared:inStagingArea ?area .
    FILTER(STR(?name) = "top")
    FILTER NOT EXISTS {{ {folder_term} shared:inStagingFolder ?parent . }}
  }} UNION {{
    {folder_term} a shared:StagingFolder ; schema:name ?name ;
      shared:inStagingArea ?area ; shared:inStagingFolder ?top .
    ?top a shared:StagingFolder ; schema:name ?topName ; shared:inStagingArea ?area .
    FILTER(STR(?name) IN ("Mobile", "Trash") && STR(?topName) = "top")
    FILTER NOT EXISTS {{ ?top shared:inStagingFolder ?parent . }}
  }}
}} }}
"""


def _mobile_folder_query(graph: StagingGraph, folder: str) -> str:
    folder_term = _iri_term(folder)
    return f"""# protected-mobile-folder
PREFIX shared: <http://oldap.org/shared#>
PREFIX schema: <https://schema.org/>
ASK {{ GRAPH {_graph_term(graph)} {{
  {folder_term} a shared:StagingFolder ; schema:name ?name ;
    shared:inStagingArea ?area ; shared:inStagingFolder ?top .
  ?top a shared:StagingFolder ; schema:name ?topName ; shared:inStagingArea ?area .
  FILTER(STR(?name) = "Mobile" && STR(?topName) = "top")
  FILTER NOT EXISTS {{ ?top shared:inStagingFolder ?parent . }}
}} }}
"""


def _deletion_target_query(graph: StagingGraph, area: str) -> str:
    return f"""# staging-area-deletion-target
PREFIX shared: <http://oldap.org/shared#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <https://schema.org/>
SELECT ?folder ?name ?parent WHERE {{
  GRAPH {_graph_term(graph)} {{
    {_iri_term(area)} a ?areaClass .
    ?folder a shared:StagingFolder ; shared:inStagingArea {_iri_term(area)} ; schema:name ?name .
    OPTIONAL {{ ?folder shared:inStagingFolder ?parent . }}
  }}
  FILTER(
    ?areaClass = shared:StagingArea ||
    EXISTS {{ GRAPH ?ontologyGraph {{ ?areaClass rdfs:subClassOf+ shared:StagingArea . }} }}
  )
}}
LIMIT 16
"""


def _admin_delete_query(graph: StagingGraph, actor: str) -> str:
    return f"""# staging-area-admin-delete
PREFIX oldap: <http://oldap.org/base#>
ASK {{ GRAPH oldap:admin {{
  {{
    ?project a oldap:Project ; oldap:projectShortName ?projectShortName .
    FILTER(STR(?projectShortName) = {Literal(graph.project_short_name).n3()})
    << {_iri_term(actor)} oldap:inProject ?project >> oldap:hasAdminPermission oldap:ADMIN_RESOURCES .
  }} UNION {{
    << {_iri_term(actor)} oldap:inProject oldap:SystemProject >> oldap:hasAdminPermission oldap:ADMIN_OLDAP .
  }}
}} }}
"""


def _staging_area_exists_query(graph: StagingGraph, area: str) -> str:
    return f"""# staging-area-exists
PREFIX shared: <http://oldap.org/shared#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
ASK {{
  GRAPH {_graph_term(graph)} {{ {_iri_term(area)} a ?areaClass . }}
  FILTER(
    ?areaClass = shared:StagingArea ||
    EXISTS {{ GRAPH ?ontologyGraph {{ ?areaClass rdfs:subClassOf+ shared:StagingArea . }} }}
  )
}}
"""


def _resource_delete_permissions_query(
    graph: StagingGraph, actor: str, target: DeletionTarget
) -> str:
    resources = " ".join(_iri_term(value) for value in target.resources)
    return f"""# staging-area-resource-delete-permissions
PREFIX oldap: <http://oldap.org/base#>
SELECT DISTINCT ?resource WHERE {{
  VALUES ?resource {{ {resources} }}
  {{ GRAPH {_graph_term(graph)} {{ ?resource oldap:createdBy {_iri_term(actor)} . }} }}
  UNION
  {{
    GRAPH oldap:admin {{
      {_iri_term(actor)} oldap:hasRole ?role .
      ?permission oldap:permissionValue ?value .
      oldap:DATA_DELETE oldap:permissionValue ?required .
      FILTER(?value >= ?required)
    }}
    GRAPH {_graph_term(graph)} {{
      ?resource oldap:attachedToRole ?role .
      << ?resource oldap:attachedToRole ?role >> oldap:hasDataPermission ?permission .
    }}
  }}
}}
"""


def _staging_contents_query(graph: StagingGraph, target: DeletionTarget) -> str:
    folders = " ".join(
        _iri_term(value) for value in (target.top, target.mobile, target.trash)
    )
    return f"""# staging-area-contents
PREFIX shared: <http://oldap.org/shared#>
ASK {{ GRAPH {_graph_term(graph)} {{
  {{
    ?resource shared:inStagingArea {_iri_term(target.area)} .
    FILTER(?resource NOT IN ({', '.join(_iri_term(value) for value in target.resources)}))
  }} UNION {{
    VALUES ?folder {{ {folders} }}
    ?resource shared:inStagingFolder ?folder .
    FILTER(?resource NOT IN ({', '.join(_iri_term(value) for value in target.resources)}))
  }}
}} }}
"""


def _external_references_query(graph: StagingGraph, target: DeletionTarget) -> str:
    targets = ", ".join(_iri_term(value) for value in target.resources)
    return f"""# staging-area-external-references
PREFIX shared: <http://oldap.org/shared#>
ASK {{ GRAPH ?graph {{
  ?source ?predicate ?target .
  FILTER(?target IN ({targets}))
  FILTER(!(
    ?graph = {_graph_term(graph)} &&
    (
      (?source IN ({_iri_term(target.top)}, {_iri_term(target.mobile)}, {_iri_term(target.trash)}) &&
       ?predicate = shared:inStagingArea && ?target = {_iri_term(target.area)})
      ||
      (?source IN ({_iri_term(target.mobile)}, {_iri_term(target.trash)}) &&
       ?predicate = shared:inStagingFolder && ?target = {_iri_term(target.top)})
    )
  ))
}} }}
"""


def _atomic_delete(graph: StagingGraph, target: DeletionTarget) -> str:
    resources = " ".join(_iri_term(value) for value in target.resources)
    return f"""# atomic-staging-area-delete
PREFIX oldap: <http://oldap.org/base#>
DELETE {{
  GRAPH {_graph_term(graph)} {{
    ?resource ?predicate ?value .
    << ?resource oldap:attachedToRole ?role >> ?annotationPredicate ?annotationValue .
  }}
}}
WHERE {{
  VALUES ?resource {{ {resources} }}
  GRAPH {_graph_term(graph)} {{
    OPTIONAL {{ ?resource ?predicate ?value . }}
    OPTIONAL {{
      ?resource oldap:attachedToRole ?role .
      << ?resource oldap:attachedToRole ?role >> ?annotationPredicate ?annotationValue .
    }}
  }}
}}
"""


def _remaining_targets_query(graph: StagingGraph, target: DeletionTarget) -> str:
    resources = " ".join(_iri_term(value) for value in target.resources)
    return f"""# remaining-staging-area-targets
PREFIX oldap: <http://oldap.org/base#>
ASK {{ GRAPH {_graph_term(graph)} {{
  VALUES ?resource {{ {resources} }}
  {{ ?resource ?predicate ?value . }}
  UNION
  {{ << ?resource oldap:attachedToRole ?role >> ?annotationPredicate ?annotationValue . }}
}} }}
"""
