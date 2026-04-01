import redis.asyncio as aioredis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from app.core.config import get_settings

settings = get_settings()

_redis_client: aioredis.Redis | None = None  # type: ignore[type-arg]


async def init_rate_limiter() -> None:
    """Connect to Redis and initialise FastAPILimiter. Called at app startup."""
    global _redis_client
    _redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    await FastAPILimiter.init(_redis_client)


async def close_rate_limiter() -> None:
    """Close Redis connection. Called at app shutdown."""
    await FastAPILimiter.close()
    if _redis_client is not None:
        await _redis_client.aclose()


async def check_redis_health() -> bool:
    """Ping Redis and return True if reachable."""
    try:
        if _redis_client is None:
            return False
        return await _redis_client.ping()  # type: ignore[return-value]
    except Exception:
        return False


def agent_rate_limiter() -> RateLimiter:
    """
    Returns a per-IP RateLimiter dependency using values from Settings.
    Usage: @router.post("/run", dependencies=[Depends(agent_rate_limiter())])
    """
    return RateLimiter(
        times=settings.rate_limit_requests,
        seconds=settings.rate_limit_seconds,
    )
