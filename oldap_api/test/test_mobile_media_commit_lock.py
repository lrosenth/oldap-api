"""Cross-worker mobile-media commit serialization tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier, Lock

import pytest
from redis.exceptions import ConnectionError, LockNotOwnedError

from oldap_api.mobile_media.commit_lock import RedisMobileMediaCommitLock
from oldap_api.mobile_media.domain import (
    MobileMediaCommitResult,
    MobileMediaServiceUnavailableError,
)
from oldap_api.mobile_media.service import MobileMediaCommitService
from oldap_api.test.test_mobile_media_domain import (
    CHECKSUM,
    CLIENT_ASSET_ID,
    EVENT_ID,
    UPLOAD_ID,
    commit_request,
)


class FakeRedisLock:
    """Expose controllable redis-py lock behaviour without a Redis service."""

    def __init__(
        self, *, acquired: bool = True, acquire_error=None, release_error=None
    ) -> None:
        self.acquired = acquired
        self.acquire_error = acquire_error
        self.release_error = release_error
        self.released = 0

    def acquire(self, *, blocking: bool):
        assert blocking is True
        if self.acquire_error is not None:
            raise self.acquire_error
        return self.acquired

    def release(self) -> None:
        self.released += 1
        if self.release_error is not None:
            raise self.release_error


class FakeRedis:
    def __init__(self, lock: FakeRedisLock) -> None:
        self.redis_lock = lock
        self.arguments = None

    def lock(self, name, *, timeout, blocking_timeout):
        self.arguments = (name, timeout, blocking_timeout)
        return self.redis_lock


def test_redis_commit_lock_uses_a_bounded_lease_and_releases_it() -> None:
    redis_lock = FakeRedisLock()
    client = FakeRedis(redis_lock)
    guard = RedisMobileMediaCommitLock(client)

    assert guard.run(lambda: "committed") == "committed"
    assert client.arguments == (
        RedisMobileMediaCommitLock.LOCK_NAME,
        RedisMobileMediaCommitLock.LEASE_SECONDS,
        RedisMobileMediaCommitLock.WAIT_SECONDS,
    )
    assert redis_lock.released == 1


@pytest.mark.parametrize(
    "redis_lock",
    [
        FakeRedisLock(acquired=False),
        FakeRedisLock(acquire_error=ConnectionError("redis unavailable")),
    ],
)
def test_unavailable_commit_coordination_fails_retryably(redis_lock) -> None:
    guard = RedisMobileMediaCommitLock(FakeRedis(redis_lock))

    with pytest.raises(MobileMediaServiceUnavailableError) as caught:
        guard.run(lambda: pytest.fail("operation must not run"))

    assert caught.value.retryable is True


def test_operation_failure_is_preserved_and_the_lease_is_released() -> None:
    redis_lock = FakeRedisLock()
    guard = RedisMobileMediaCommitLock(FakeRedis(redis_lock))

    with pytest.raises(ValueError, match="transaction failed"):
        guard.run(lambda: (_ for _ in ()).throw(ValueError("transaction failed")))

    assert redis_lock.released == 1


def test_lost_lease_after_a_commit_returns_a_retryable_reconciliation_error() -> None:
    redis_lock = FakeRedisLock(
        release_error=LockNotOwnedError("lease expired before release")
    )
    guard = RedisMobileMediaCommitLock(FakeRedis(redis_lock))

    with pytest.raises(MobileMediaServiceUnavailableError) as caught:
        guard.run(lambda: "durable GraphDB result")

    assert caught.value.retryable is True
    assert redis_lock.released == 1


def test_concurrent_exact_commits_observe_one_durable_logical_result() -> None:
    """Model four API workers sharing one serialized receipt boundary."""

    class ThreadCommitLock:
        def __init__(self) -> None:
            self.lock = Lock()

        def run(self, operation):
            with self.lock:
                return operation()

    class DurableRepository:
        def __init__(self) -> None:
            self.result = None
            self.created = 0

        def commit(self, commit, *, committed_at=None):
            if self.result is None:
                self.created += 1
                self.result = MobileMediaCommitResult(
                    event_id=commit.event_id,
                    upload_id=commit.upload_id,
                    client_asset_id=commit.client_asset_id,
                    staging_area_id=commit.staging_area_id,
                    asset_id=commit.client_asset_id,
                    resource_iri=commit.resource_iri,
                    checksum=commit.checksum,
                    committed_at=datetime(2026, 8, 20, 16, 0, tzinfo=UTC),
                )
            return self.result

    repository = DurableRepository()
    service = MobileMediaCommitService(repository, ThreadCommitLock())
    start = Barrier(4)

    def commit_once():
        start.wait()
        return service.commit(UPLOAD_ID, commit_request())

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: commit_once(), range(4)))

    assert repository.created == 1
    assert all(result == results[0] for result in results)
    assert results[0].event_id == EVENT_ID
    assert results[0].client_asset_id == CLIENT_ASSET_ID
    assert results[0].checksum == CHECKSUM
