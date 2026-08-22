"""Cross-process serialization for idempotent mobile-media commits."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from redis import Redis
from redis.exceptions import LockError, RedisError

from oldap_api.staging_lock import (
    STAGING_MUTATION_LEASE_SECONDS,
    STAGING_MUTATION_LOCK_NAME,
    STAGING_MUTATION_WAIT_SECONDS,
)
from oldap_api.redis_config import staging_lock_redis_url

from .domain import MobileMediaServiceUnavailableError

T = TypeVar("T")


class RedisMobileMediaCommitLock:
    """Serialize GraphDB check-and-insert transactions across API workers.

    GraphDB exposes read-committed transactions, so two workers can otherwise
    both observe an absent receipt before either transaction commits. A single
    short Redis lease closes that race. The permanent GraphDB receipt remains
    the source of truth; Redis holds no result or ownership data.
    """

    LOCK_NAME = STAGING_MUTATION_LOCK_NAME
    LEASE_SECONDS = STAGING_MUTATION_LEASE_SECONDS
    WAIT_SECONDS = STAGING_MUTATION_WAIT_SECONDS

    def __init__(self, client: Redis | None = None) -> None:
        self._client = client or Redis.from_url(
            staging_lock_redis_url(),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    def run(self, operation: Callable[[], T]) -> T:
        """Run one commit while holding the bounded global write lease."""

        lock = self._client.lock(
            self.LOCK_NAME,
            timeout=self.LEASE_SECONDS,
            blocking_timeout=self.WAIT_SECONDS,
        )
        try:
            acquired = lock.acquire(blocking=True)
        except RedisError as error:
            raise MobileMediaServiceUnavailableError(
                "Mobile-media commit coordination is unavailable."
            ) from error
        if not acquired:
            raise MobileMediaServiceUnavailableError(
                "Another mobile-media commit is still active."
            )

        try:
            result = operation()
        except Exception:
            try:
                lock.release()
            except (LockError, RedisError):
                pass
            raise

        try:
            lock.release()
        except (LockError, RedisError) as error:
            # The GraphDB result may already be durable. Returning retryable 503
            # makes the caller resolve the permanent receipt on its next attempt.
            raise MobileMediaServiceUnavailableError(
                "Mobile-media commit coordination was lost."
            ) from error
        return result
