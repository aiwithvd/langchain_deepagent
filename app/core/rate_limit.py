"""
Rate limiting backed by Redis (pyrate_limiter + fastapi-limiter v0.2).

On startup:
  - Connects to Redis and builds a per-IP RedisBucket-based Limiter.
  - If Redis is unreachable, falls back to an InMemoryBucket limiter with a warning.

Usage in routes:
    @router.post("/run", dependencies=[Depends(get_rate_limiter())])
"""

from __future__ import annotations

import redis.asyncio as aioredis
import redis as sync_redis
from pyrate_limiter import (
    BucketFactory,
    Duration,
    InMemoryBucket,
    Limiter,
    Rate,
    RateItem,
    RedisBucket,
    SingleBucketFactory,
)
from fastapi_limiter.depends import RateLimiter

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
log = get_logger(__name__)

_limiter: Limiter | None = None
_redis_client: aioredis.Redis | None = None  # type: ignore[type-arg]


def _build_rates() -> list[Rate]:
    return [Rate(settings.rate_limit_requests, Duration.SECOND * settings.rate_limit_seconds)]


def _make_in_memory_limiter() -> Limiter:
    rates = _build_rates()
    bucket = InMemoryBucket(rates)
    factory = SingleBucketFactory(bucket)
    return Limiter(factory)


async def _make_redis_limiter() -> Limiter:
    """Build a Limiter backed by Redis. Raises on connection failure."""
    rates = _build_rates()

    # Sync Redis client needed for RedisBucket.init (which uses script_load)
    r_sync = sync_redis.from_url(settings.redis_url, decode_responses=False)
    bucket = RedisBucket.init(rates, r_sync, "deepagent:ratelimit")

    factory = SingleBucketFactory(bucket, schedule_leak=False)
    return Limiter(factory)


async def init_rate_limiter() -> None:
    """
    Initialise the global rate limiter at app startup.
    Tries Redis first; falls back to in-memory if unavailable.
    """
    global _limiter, _redis_client

    # Keep an async client for health checks
    _redis_client = aioredis.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )

    try:
        await _redis_client.ping()
        _limiter = await _make_redis_limiter()
        log.info("Rate limiter using Redis backend", redis_url=settings.redis_url)
    except Exception as exc:
        log.warning(
            "Redis unreachable — falling back to in-memory rate limiter",
            error=str(exc),
        )
        _limiter = _make_in_memory_limiter()


async def close_rate_limiter() -> None:
    """Close Redis connection on app shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def check_redis_health() -> bool:
    """Ping Redis and return True if reachable."""
    try:
        if _redis_client is None:
            return False
        return bool(await _redis_client.ping())
    except Exception:
        return False


def get_rate_limiter() -> RateLimiter:
    """
    Returns a per-route RateLimiter dependency.
    The limiter instance is resolved at request time (after init_rate_limiter runs).

    Usage:
        @router.post("/run", dependencies=[Depends(get_rate_limiter())])
    """
    if _limiter is None:
        # Should not happen after startup, but guard defensively
        fallback = _make_in_memory_limiter()
        return RateLimiter(limiter=fallback)
    return RateLimiter(limiter=_limiter)
