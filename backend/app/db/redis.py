"""Redis async client for caching and session management."""

import redis.asyncio as redis

from app.config import settings

redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Get or create the Redis client singleton (lazy init)."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


async def close_redis() -> None:
    """Close the Redis connection if open."""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None


async def get_redis() -> redis.Redis:
    """FastAPI dependency that returns the Redis client."""
    return get_redis_client()
