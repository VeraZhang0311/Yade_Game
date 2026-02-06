"""Redis async client for caching and session management."""

import redis.asyncio as redis

from app.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> redis.Redis:
    """Dependency that returns the Redis client."""
    return redis_client
