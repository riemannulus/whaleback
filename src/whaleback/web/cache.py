"""Cache service abstraction with Redis and in-memory fallback."""

import json
import logging
from typing import Any

from cachetools import TTLCache

logger = logging.getLogger(__name__)


class CacheService:
    """Unified cache interface supporting Redis or in-memory TTLCache."""

    def __init__(self, redis_client=None, ttl: int = 300):
        self._redis = redis_client
        self._ttl = ttl
        self._memory = TTLCache(maxsize=2048, ttl=ttl)
        self._using_redis = redis_client is not None

    @classmethod
    async def create(cls, redis_url: str, ttl: int = 300) -> "CacheService":
        """Factory method that tries Redis, falls back to in-memory."""
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(redis_url, decode_responses=True)
            await client.ping()
            logger.info("Cache: Connected to Redis")
            return cls(redis_client=client, ttl=ttl)
        except Exception as e:
            logger.warning(f"Cache: Redis unavailable ({e}), using in-memory TTLCache")
            return cls(redis_client=None, ttl=ttl)

    async def get(self, key: str) -> Any | None:
        """Get cached value by key."""
        if self._using_redis:
            try:
                value = await self._redis.get(key)
                if value is not None:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Cache get error: {e}")
        else:
            return self._memory.get(key)
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set cached value with optional custom TTL."""
        ttl = ttl or self._ttl
        if self._using_redis:
            try:
                await self._redis.setex(key, ttl, json.dumps(value, default=str))
            except Exception as e:
                logger.warning(f"Cache set error: {e}")
        else:
            self._memory[key] = value

    async def delete(self, key: str) -> None:
        """Delete a cached key."""
        if self._using_redis:
            try:
                await self._redis.delete(key)
            except Exception as e:
                logger.warning(f"Cache delete error: {e}")
        else:
            self._memory.pop(key, None)

    async def clear_prefix(self, prefix: str) -> None:
        """Delete all keys matching a prefix."""
        if self._using_redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=f"{prefix}*", count=100)
                    if keys:
                        await self._redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Cache clear_prefix error: {e}")
        else:
            keys_to_delete = [k for k in self._memory if k.startswith(prefix)]
            for k in keys_to_delete:
                self._memory.pop(k, None)

    async def close(self) -> None:
        """Close the cache connection."""
        if self._using_redis and self._redis:
            await self._redis.close()

    @property
    def is_redis(self) -> bool:
        return self._using_redis
