"""Redis cache and Staging-lock database isolation tests."""

import pytest

import oldap_api
from oldap_api.mobile_media.commit_lock import RedisMobileMediaCommitLock
from oldap_api.redis_config import (
    RedisConfigurationError,
    redis_database_identity,
    staging_lock_redis_url,
    validate_redis_database_separation,
)
from oldap_api.staging_lock import RedisStagingMutationLock


def test_default_database_and_explicit_zero_are_identical() -> None:
    """Redis URLs without a path select logical database zero."""

    assert redis_database_identity("redis://cache:6379") == redis_database_identity(
        "redis://cache:6379/0"
    )


def test_credentials_do_not_hide_an_identical_database() -> None:
    """Authentication differences do not make one database independent."""

    assert redis_database_identity(
        "redis://first:secret@cache:6379/0"
    ) == redis_database_identity("redis://second:other@cache:6379/0")


def test_transport_mode_does_not_hide_an_identical_database() -> None:
    """TLS selection cannot bypass logical database separation validation."""

    assert redis_database_identity("redis://cache:6379/0") == redis_database_identity(
        "rediss://cache:6379/0"
    )


def test_separate_logical_databases_are_accepted(monkeypatch) -> None:
    """One API-owned Redis server may safely provide cache DB 0 and lock DB 1."""

    monkeypatch.setenv("OLDAP_REDIS_URL", "redis://cache:6379/0")
    monkeypatch.setenv("OLDAP_STAGING_LOCK_REDIS_URL", "redis://cache:6379/1")

    validate_redis_database_separation(production=True)
    assert staging_lock_redis_url() == "redis://cache:6379/1"


def test_identical_cache_and_lock_database_is_rejected(monkeypatch) -> None:
    """Prevent CacheSingletonRedis.flushdb from deleting an active lock."""

    monkeypatch.setenv("OLDAP_REDIS_URL", "redis://cache:6379")
    monkeypatch.setenv("OLDAP_STAGING_LOCK_REDIS_URL", "redis://cache:6379/0")

    with pytest.raises(RedisConfigurationError, match="different logical"):
        validate_redis_database_separation(production=True)


def test_production_requires_an_explicit_lock_database(monkeypatch) -> None:
    """Production must not rely on a localhost-oriented development default."""

    monkeypatch.setenv("OLDAP_REDIS_URL", "redis://cache:6379/0")
    monkeypatch.delenv("OLDAP_STAGING_LOCK_REDIS_URL", raising=False)

    with pytest.raises(RedisConfigurationError, match="OLDAP_STAGING_LOCK_REDIS_URL"):
        validate_redis_database_separation(production=True)


def test_both_staging_guards_use_only_the_dedicated_lock_url(monkeypatch) -> None:
    """Keep cache Redis configuration out of every Staging lock client."""

    configured_url = "redis://api-redis:6379/1"
    clients = []

    def build_client(url, **options):
        clients.append((url, options))
        return object()

    monkeypatch.setenv("OLDAP_REDIS_URL", "redis://api-redis:6379/0")
    monkeypatch.setenv("OLDAP_STAGING_LOCK_REDIS_URL", configured_url)
    monkeypatch.setattr("oldap_api.staging_lock.Redis.from_url", build_client)

    RedisStagingMutationLock()
    RedisMobileMediaCommitLock()

    assert [url for url, _ in clients] == [configured_url, configured_url]


def test_application_rejects_overlap_before_clearing_cache(monkeypatch) -> None:
    """A bad production configuration must fail before oldaplib calls FLUSHDB."""

    class UnexpectedCache:
        def __init__(self):
            raise AssertionError("cache must not be opened before validation")

    monkeypatch.setenv("APP_ENV", "Prod")
    monkeypatch.setenv("OLDAP_REDIS_URL", "redis://api-redis:6379/0")
    monkeypatch.setenv("OLDAP_STAGING_LOCK_REDIS_URL", "redis://api-redis:6379/0")
    monkeypatch.setattr(oldap_api, "CacheSingletonRedis", UnexpectedCache)

    with pytest.raises(RedisConfigurationError, match="different logical"):
        oldap_api.create_app()
