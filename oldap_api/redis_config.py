"""Redis database isolation for API cache and Staging coordination."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from redis import Redis

CACHE_REDIS_ENV = "OLDAP_REDIS_URL"
STAGING_LOCK_REDIS_ENV = "OLDAP_STAGING_LOCK_REDIS_URL"
DEFAULT_CACHE_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_STAGING_LOCK_REDIS_URL = "redis://localhost:6379/1"


class RedisConfigurationError(RuntimeError):
    """Raised when cache clearing could invalidate a Staging mutation lock."""


@dataclass(frozen=True)
class RedisDatabaseIdentity:
    """Identify one logical Redis database without retaining credentials."""

    transport: str
    endpoint: str
    port: int | None
    database: int


def staging_lock_redis_url() -> str:
    """Return the API-owned Redis URL reserved for Staging coordination."""

    return os.getenv(STAGING_LOCK_REDIS_ENV, DEFAULT_STAGING_LOCK_REDIS_URL)


def redis_database_identity(url: str) -> RedisDatabaseIdentity:
    """Normalize the server and logical database addressed by a Redis URL."""

    try:
        client = Redis.from_url(url)
        options = client.connection_pool.connection_kwargs
        parsed = urlsplit(url)
        database = int(options.get("db", 0))
    except (TypeError, ValueError) as error:
        raise RedisConfigurationError("A Redis database URL is invalid.") from error

    scheme = parsed.scheme.lower()
    if scheme == "unix":
        transport = "unix"
        endpoint = str(options.get("path", parsed.path))
        port = None
    else:
        transport = "tcp"
        endpoint = str(options.get("host", parsed.hostname or "localhost")).lower()
        port = int(options.get("port", parsed.port or 6379))
    return RedisDatabaseIdentity(transport, endpoint, port, database)


def validate_redis_database_separation(*, production: bool) -> None:
    """Fail before startup if cache flushes could remove a coordination lock."""

    lock_url = os.getenv(STAGING_LOCK_REDIS_ENV)
    if production and not lock_url:
        raise RedisConfigurationError(
            f"{STAGING_LOCK_REDIS_ENV} must be configured in production."
        )

    cache_identity = redis_database_identity(
        os.getenv(CACHE_REDIS_ENV, DEFAULT_CACHE_REDIS_URL)
    )
    lock_identity = redis_database_identity(lock_url or DEFAULT_STAGING_LOCK_REDIS_URL)
    if cache_identity == lock_identity:
        raise RedisConfigurationError(
            "OLDAP cache and Staging coordination must use different logical "
            "Redis databases."
        )
