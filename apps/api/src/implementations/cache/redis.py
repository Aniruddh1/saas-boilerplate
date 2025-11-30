"""
Redis cache backend implementation.
"""

from __future__ import annotations

import json
import asyncio
from typing import Any, Callable, Awaitable, TypeVar
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio.lock import Lock as RedisLock

T = TypeVar("T")


class RedisCacheLock:
    """Redis distributed lock wrapper."""

    def __init__(self, lock: RedisLock):
        self._lock = lock

    async def acquire(self) -> bool:
        return await self._lock.acquire()

    async def release(self) -> bool:
        try:
            await self._lock.release()
            return True
        except redis.exceptions.LockError:
            return False

    async def extend(self, additional_time: int) -> bool:
        try:
            await self._lock.extend(additional_time)
            return True
        except redis.exceptions.LockError:
            return False

    async def __aenter__(self) -> "RedisCacheLock":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.release()


class RedisCacheBackend:
    """
    Redis cache backend implementation.

    Usage:
        cache = RedisCacheBackend(redis_url="redis://localhost:6379/0")
        await cache.connect()

        await cache.set("key", {"data": "value"}, ttl=300)
        value = await cache.get("key")

        # Cache-aside pattern
        user = await cache.get_or_set(
            f"user:{user_id}",
            lambda: db.get_user(user_id),
            ttl=600,
        )

        # Distributed lock
        async with await cache.lock("process:123"):
            # Only one process runs this at a time
            await do_exclusive_work()
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "",
        default_ttl: int = 3600,
    ):
        self.redis_url = redis_url
        self.prefix = prefix
        self.default_ttl = default_ttl
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")
        return self._client

    def _key(self, key: str) -> str:
        """Prepend prefix to key."""
        return f"{self.prefix}{key}" if self.prefix else key

    def _ttl_seconds(self, ttl: int | timedelta | None) -> int | None:
        """Convert TTL to seconds."""
        if ttl is None:
            return self.default_ttl
        if isinstance(ttl, timedelta):
            return int(ttl.total_seconds())
        return ttl

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value)

    def _deserialize(self, value: str | None) -> Any:
        """Deserialize JSON string to value."""
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def get(self, key: str) -> Any | None:
        """Get value by key."""
        value = await self.client.get(self._key(key))
        return self._deserialize(value)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | timedelta | None = None,
    ) -> bool:
        """Set value with optional TTL."""
        ttl_seconds = self._ttl_seconds(ttl)
        serialized = self._serialize(value)
        result = await self.client.set(
            self._key(key),
            serialized,
            ex=ttl_seconds,
        )
        return result is True

    async def delete(self, key: str) -> bool:
        """Delete key."""
        result = await self.client.delete(self._key(key))
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        result = await self.client.exists(self._key(key))
        return result > 0

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple keys."""
        if not keys:
            return {}

        prefixed_keys = [self._key(k) for k in keys]
        values = await self.client.mget(prefixed_keys)

        result = {}
        for key, value in zip(keys, values):
            if value is not None:
                result[key] = self._deserialize(value)
        return result

    async def set_many(
        self,
        mapping: dict[str, Any],
        ttl: int | timedelta | None = None,
    ) -> bool:
        """Set multiple key-value pairs."""
        if not mapping:
            return True

        ttl_seconds = self._ttl_seconds(ttl)
        pipe = self.client.pipeline()

        for key, value in mapping.items():
            serialized = self._serialize(value)
            pipe.set(self._key(key), serialized, ex=ttl_seconds)

        await pipe.execute()
        return True

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple keys."""
        if not keys:
            return 0
        prefixed_keys = [self._key(k) for k in keys]
        return await self.client.delete(*prefixed_keys)

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        prefixed_pattern = self._key(pattern)
        keys = []

        async for key in self.client.scan_iter(match=prefixed_pattern):
            keys.append(key)

        if keys:
            return await self.client.delete(*keys)
        return 0

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment integer value."""
        return await self.client.incrby(self._key(key), amount)

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement integer value."""
        return await self.client.decrby(self._key(key), amount)

    async def ttl(self, key: str) -> int | None:
        """Get remaining TTL in seconds."""
        result = await self.client.ttl(self._key(key))
        if result < 0:  # -1 no TTL, -2 key doesn't exist
            return None
        return result

    async def expire(self, key: str, ttl: int | timedelta) -> bool:
        """Set/update TTL on existing key."""
        ttl_seconds = self._ttl_seconds(ttl)
        return await self.client.expire(self._key(key), ttl_seconds)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl: int | timedelta | None = None,
    ) -> T:
        """Get from cache or call factory and cache result."""
        value = await self.get(key)
        if value is not None:
            return value

        # Cache miss - call factory
        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value

    async def lock(
        self,
        key: str,
        ttl: int = 30,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> RedisCacheLock:
        """Acquire distributed lock."""
        lock = self.client.lock(
            self._key(f"lock:{key}"),
            timeout=ttl,
            blocking=blocking,
            blocking_timeout=timeout,
        )
        return RedisCacheLock(lock)
