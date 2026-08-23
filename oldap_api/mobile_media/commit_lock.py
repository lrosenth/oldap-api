"""Cross-process serialization for idempotent mobile-media commits."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from redis import Redis

from oldap_api.staging_lock import (
    RedisStagingMutationLock,
    STAGING_MUTATION_LEASE_SECONDS,
    STAGING_MUTATION_LOCK_NAME,
    STAGING_MUTATION_WAIT_SECONDS,
    StagingMutationLockUnavailable,
)

from .domain import MobileMediaServiceUnavailableError

T = TypeVar("T")


class RedisMobileMediaCommitLock:
    """Serialize GraphDB check-and-insert transactions across API workers.

    GraphDB exposes read-committed transactions, so two workers can otherwise
    both observe an absent receipt before either transaction commits. The
    common bounded, heartbeat-renewed Staging Redis lease closes that race.
    The permanent GraphDB receipt remains the source of truth; Redis holds no
    result or ownership data.
    """

    LOCK_NAME = STAGING_MUTATION_LOCK_NAME
    LEASE_SECONDS = STAGING_MUTATION_LEASE_SECONDS
    WAIT_SECONDS = STAGING_MUTATION_WAIT_SECONDS

    def __init__(self, client: Redis | None = None) -> None:
        self._lock = RedisStagingMutationLock(client)

    def run(self, operation: Callable[[], T]) -> T:
        """Run one commit while holding the bounded global write lease."""

        try:
            return self._lock.run(operation)
        except StagingMutationLockUnavailable as error:
            raise MobileMediaServiceUnavailableError(
                "Mobile-media commit coordination is unavailable."
            ) from error
