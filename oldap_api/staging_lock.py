"""Cross-worker coordination for writes that affect Staging structure."""

from __future__ import annotations

import logging
from collections.abc import Callable
from threading import Event, Thread
from typing import TypeVar

from redis import Redis
from redis.exceptions import LockError, RedisError

from oldap_api.redis_config import staging_lock_redis_url

T = TypeVar("T")

STAGING_MUTATION_LOCK_NAME = "oldap-api:staging:mutation"
STAGING_MUTATION_LEASE_SECONDS = 300
STAGING_MUTATION_WAIT_SECONDS = 30


class StagingMutationLockUnavailable(RuntimeError):
    """Raised before a Staging write when cross-worker coordination is unavailable."""


class RedisStagingMutationLock:
    """Serialize Staging structure writes across API workers.

    GraphDB transactions use read-committed isolation. The bounded Redis lease
    therefore protects check-then-write operations from concurrent folder,
    media, and StagingArea mutations. GraphDB remains the durable source of
    truth; Redis stores neither resources nor operation results.
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
        """Run one Staging mutation while holding the bounded global lease."""

        lock = self._client.lock(
            self.LOCK_NAME,
            timeout=self.LEASE_SECONDS,
            blocking_timeout=self.WAIT_SECONDS,
            thread_local=False,
        )
        try:
            acquired = lock.acquire(blocking=True)
        except RedisError as error:
            raise StagingMutationLockUnavailable(
                "Staging write coordination is unavailable."
            ) from error
        if not acquired:
            raise StagingMutationLockUnavailable(
                "Another Staging write is still active."
            )

        renewal_stop = Event()
        renewal_failed = Event()

        def renew_lease() -> None:
            interval = max(1, self.LEASE_SECONDS // 3)
            while not renewal_stop.wait(interval):
                try:
                    lock.extend(self.LEASE_SECONDS, replace_ttl=True)
                except (LockError, RedisError):
                    renewal_failed.set()
                    return

        renewal = Thread(
            target=renew_lease,
            name="oldap-staging-mutation-lease",
            daemon=True,
        )
        renewal.start()
        try:
            result = operation()
        except BaseException:
            renewal_stop.set()
            renewal.join()
            try:
                lock.release()
            except (LockError, RedisError):
                pass
            raise

        renewal_stop.set()
        renewal.join()
        if renewal_failed.is_set():
            logging.getLogger(__name__).error(
                "Staging mutation lease renewal failed during an active write."
            )
        try:
            lock.release()
        except (LockError, RedisError):
            # The operation may already be durable. Keep its truthful success
            # response; the bounded lease expires without storing domain data.
            logging.getLogger(__name__).warning(
                "Staging mutation lease could not be released after a successful write."
            )
        return result
