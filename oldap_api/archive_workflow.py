"""Authenticated application services for archive YAML HTTP workflows."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from oldaplib.src.archive_import import (
    ArchiveImportPlan,
    apply_archive_import,
    prepare_archive_import,
)
from oldaplib.src.archive_yaml import archive_yaml_hash, dumps_archive_yaml, loads_archive_yaml
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorValue
from oldaplib.src.objectfactory import CompOp, ResourceInstance, ResourceInstanceFactory, SearchFilter
from oldaplib.src.project import Project
from oldaplib.src.staging_archive import (
    ArchiveProposal,
    StagingFolderSnapshot,
    staging_folders_to_archive_proposal,
)
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def _value(record: dict[Any, Any], property_name: str) -> Any | None:
    """Return the first projected value regardless of QName/string keys."""

    values = next((value for key, value in record.items() if str(key) == property_name), None)
    if isinstance(values, (list, tuple, set)):
        return next(iter(values), None)
    return values


def _class_is_or_extends(instance: Any, expected: Xsd_QName) -> bool:
    """Check the dynamic ResourceInstance class and its declared superclasses."""

    instance_class = instance.__class__
    if instance_class.name == expected:
        return True

    def contains(superclasses: dict[Any, Any]) -> bool:
        for iri, superclass in (superclasses or {}).items():
            if iri == expected:
                return True
            if superclass is not None and contains(getattr(superclass, "superclass", {})):
                return True
        return False

    return contains(getattr(instance_class, "superclass", {}))


def build_visible_staging_archive_proposal(
    connection: Any,
    project_id: str,
    staging_area_iri: str,
) -> ArchiveProposal:
    """Read a visible StagingArea and return its read-only archive proposal.

    All reads use the request's authenticated OLDAP connection. Generic OLDAP
    search therefore excludes folders and media below ``DATA_VIEW`` without a
    privileged service identity or a second authorization model.
    """

    project = Xsd_NCName(project_id, validate=True)
    area_iri = Iri(staging_area_iri, validate=True)
    factory = ResourceInstanceFactory(con=connection, project=project)
    area = factory.read(area_iri)
    if not _class_is_or_extends(area, Xsd_QName("shared:StagingArea", validate=False)):
        raise OldapErrorNotFound("The selected StagingArea was not found.")

    area_filter = [
        SearchFilter(
            prop=Xsd_QName("shared:inStagingArea", validate=False),
            op=CompOp.EQ,
            value=area_iri,
        )
    ]
    folder_rows = ResourceInstance.search(
        con=connection,
        project=project,
        resClass=Xsd_QName("shared:StagingFolder", validate=False),
        includeProperties={
            Xsd_QName("schema:name", validate=False),
            Xsd_QName("shared:inStagingFolder", validate=False),
            Xsd_QName("schema:position", validate=False),
        },
        filter=area_filter,
        limit=5000,
    )
    media_rows = ResourceInstance.search(
        con=connection,
        project=project,
        resClass=Xsd_QName("shared:StagingMediaObject", validate=False),
        includeProperties={Xsd_QName("shared:inStagingFolder", validate=False)},
        filter=area_filter,
        limit=10000,
    )
    if not isinstance(folder_rows, list) or not isinstance(media_rows, list):
        raise OldapErrorValue("Unexpected Staging search result.")

    visible_media = Counter(
        str(folder)
        for record in media_rows
        if (folder := _value(record, "shared:inStagingFolder")) is not None
    )
    folders: list[StagingFolderSnapshot] = []
    for record in folder_rows:
        iri = _value(record, "iri")
        name = _value(record, "schema:name")
        if iri is None or name is None:
            continue
        parent = _value(record, "shared:inStagingFolder")
        position = _value(record, "schema:position")
        folders.append(
            StagingFolderSnapshot(
                iri=str(iri),
                name=str(name),
                parent_iri=str(parent) if parent is not None else None,
                position=int(position) if isinstance(position, (int, Xsd_integer)) else None,
                visible_media_count=visible_media[str(iri)],
            )
        )
    return staging_folders_to_archive_proposal(folders)


def render_archive_proposal(proposal: ArchiveProposal) -> str:
    """Render canonical YAML with editorial warnings as safe YAML comments."""

    comments = [
        "# Editorial archive structure proposal generated from visible Staging folders.",
        "# Archive levels are suggestions and must be reviewed before import.",
        "# No media were converted and generating this file changed no OLDAP data.",
    ]
    comments.extend(
        f"# WARNING [{warning.code}]: {warning.message.replace(chr(10), ' ')}"
        for warning in proposal.warnings
    )
    return "\n".join(comments) + "\n" + dumps_archive_yaml(proposal.document)


@dataclass(frozen=True)
class PreparedArchiveUpload:
    """HTTP-facing binding of exact YAML text to a central import plan."""

    document_hash: str
    plan: ArchiveImportPlan


def prepare_archive_upload(
    connection: Any,
    project_id: str,
    yaml_text: str,
    *,
    max_units: int = 5000,
) -> PreparedArchiveUpload:
    """Parse and preflight uploaded YAML without performing writes."""

    document = loads_archive_yaml(yaml_text)
    unit_count = 0
    pending = list(document.units)
    while pending:
        unit = pending.pop()
        unit_count += 1
        if unit_count > max_units:
            raise ValueError(f"Archive YAML contains more than {max_units} units.")
        pending.extend(unit.children)
    project = Project.read(connection, project_id, ignore_cache=True)
    factory = ResourceInstanceFactory(con=connection, project=project)
    plan = prepare_archive_import(
        factory,
        project_id,
        document,
        project_shortname=project.projectShortName,
    )
    return PreparedArchiveUpload(archive_yaml_hash(yaml_text), plan)


def apply_archive_upload(
    connection: Any,
    project_id: str,
    yaml_text: str,
    expected_hash: str,
) -> tuple[PreparedArchiveUpload, tuple[Iri, ...]]:
    """Bind exact YAML to its hash, repeat preflight, and apply create-only."""

    actual_hash = archive_yaml_hash(yaml_text)
    if actual_hash != expected_hash:
        raise ValueError("Archive YAML does not match the preflight document hash.")
    prepared = prepare_archive_upload(connection, project_id, yaml_text)
    factory = ResourceInstanceFactory(
        con=connection,
        project=prepared.plan.project_shortname,
    )
    return prepared, apply_archive_import(factory, prepared.plan)


def archive_plan_json(prepared: PreparedArchiveUpload) -> dict[str, Any]:
    """Serialize the reviewed creation order without exposing hidden data."""

    return {
        "documentHash": prepared.document_hash,
        "project": prepared.plan.project_id,
        "unitCount": len(prepared.plan.units),
        "externalParents": [str(iri) for iri in prepared.plan.external_parent_iris],
        "units": [
            {
                "order": index,
                "id": unit.unit_id,
                "iri": str(unit.iri),
                "level": unit.level,
                "parentIri": str(unit.parent_iri) if unit.parent_iri else None,
            }
            for index, unit in enumerate(prepared.plan.units, start=1)
        ],
        "warnings": [],
    }
