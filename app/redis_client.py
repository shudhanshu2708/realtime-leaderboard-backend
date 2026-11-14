import redis.asyncio as aioredis

from .config import settings


def create_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)
