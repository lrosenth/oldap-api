"""Application service for the atomic internal mobile-media operation."""

from __future__ import annotations

from datetime import datetime
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from .domain import (
    MobileMediaCommit,
    MobileMediaCommitResult,
    validate_mobile_media_commit,
)


class MobileMediaRepository(Protocol):
    """Atomic persistence boundary consumed by the HTTP-independent service."""

    def commit(
        self, commit: MobileMediaCommit, *, committed_at: datetime | None = None
    ) -> MobileMediaCommitResult: ...


T = TypeVar("T")


class MobileMediaCommitLock(Protocol):
    """Cross-worker boundary around receipt lookup and GraphDB insertion."""

    def run(self, operation: Callable[[], T]) -> T: ...


class MobileMediaCommitService:
    """Validate a closed request before delegating one atomic transaction."""

    def __init__(
        self,
        repository: MobileMediaRepository,
        commit_lock: MobileMediaCommitLock,
    ) -> None:
        self._repository = repository
        self._commit_lock = commit_lock

    def commit(
        self,
        upload_id: str,
        data: Any,
        *,
        committed_at: datetime | None = None,
    ) -> MobileMediaCommitResult:
        """Validate and atomically create or exactly replay one mobile medium."""

        commit = validate_mobile_media_commit(upload_id, data)
        return self._commit_lock.run(
            lambda: self._repository.commit(commit, committed_at=committed_at)
        )
