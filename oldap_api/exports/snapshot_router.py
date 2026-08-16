"""Route shared export operations to selection-kind-specific projectors."""

from __future__ import annotations

from typing import Any

from .domain import ExportKind
from .manifest import ExportManifest
from .snapshot_common import ExportSnapshotError


class ExportSnapshotRouter:
    """Compose Staging and Archive projectors behind one service boundary."""

    def __init__(self, staging_projector: Any, archive_projector: Any) -> None:
        self._staging = staging_projector
        self._archive = archive_projector

    def project(self, connection: Any, **kwargs: Any) -> Any:
        """Dispatch using only the closed shared ExportKind enumeration."""

        kind = kwargs.get("kind")
        if kind in {ExportKind.STAGING_FOLDER, ExportKind.STAGING_ALL}:
            return self._staging.project(connection, **kwargs)
        if kind in {ExportKind.ARCHIVE_UNIT, ExportKind.ARCHIVE_ALL}:
            return self._archive.project(connection, **kwargs)
        raise ExportSnapshotError("Unsupported export kind.")


class ExportDownloadAuthorizerRouter:
    """Dispatch live source reauthorization by the immutable job kind."""

    def __init__(self, staging_authorizer: Any, archive_authorizer: Any) -> None:
        self._staging = staging_authorizer
        self._archive = archive_authorizer

    def authorize(
        self,
        connection: Any,
        *,
        job: Any,
        manifest: ExportManifest,
    ) -> None:
        """Delegate without weakening either domain-specific authorization."""

        if job.selection.kind in {ExportKind.STAGING_FOLDER, ExportKind.STAGING_ALL}:
            self._staging.authorize(connection, job=job, manifest=manifest)
            return
        if job.selection.kind in {ExportKind.ARCHIVE_UNIT, ExportKind.ARCHIVE_ALL}:
            self._archive.authorize(connection, job=job, manifest=manifest)
            return
        raise ExportSnapshotError("Unsupported export kind.")


__all__ = ["ExportDownloadAuthorizerRouter", "ExportSnapshotRouter"]
