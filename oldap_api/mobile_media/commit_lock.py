"""Cross-process serialization for idempotent mobile-media commits."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TypeVar

from redis import Redis
from redis.exceptions import LockError, RedisError

from .domain import MobileMediaServiceUnavailableError

T = TypeVar("T")


class RedisMobileMediaCommitLock:
    """Serialize GraphDB check-and-insert transactions across API workers.

    GraphDB exposes read-committed transactions, so two workers can otherwise
    both observe an absent receipt before either transaction commits. A single
    short Redis lease closes that race. The permanent GraphDB receipt remains
    the source of truth; Redis holds no result or ownership data.
    """

    LOCK_NAME = "oldap-api:mobile-media:commit"
    LEASE_SECONDS = 300
    WAIT_SECONDS = 30

    def __init__(self, client: Redis | None = None) -> None:
        self._client = client or Redis.from_url(
            os.getenv("OLDAP_REDIS_URL", "redis://localhost:6379"),
            decode_responses=True,
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
