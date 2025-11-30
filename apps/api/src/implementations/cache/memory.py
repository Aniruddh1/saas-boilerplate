"""
In-memory cache backend for development and testing.
"""

from __future__ import annotations

import asyncio
import fnmatch
from typing import Any, Callable, Awaitable, TypeVar
from datetime import datetime, timedelta
from dataclasses import dataclass

T = TypeVar("T")


@dataclass
class CacheEntry:
    """Cache entry with value and expiration."""
    value: Any
    expires_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at


class MemoryCacheLock:
    """Simple in-memory lock for testing."""

    _locks: dict[str, asyncio.Lock] = {}

    def __init__(self, key: str, ttl: int):
        self.key = key
        self.ttl = ttl
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        self._lock = self._locks[key]
        self._acquired = False

    async def acquire(self) -> bool:
        self._acquired = await self._lock.acquire()
        return self._acquired

    async def release(self) -> bool:
        if self._acquired:
            self._lock.release()
            self._acquired = False
            return True
        return False

    async def extend(self, additional_time: int) -> bool:
        return self._acquired

    async def __aenter__(self) -> "MemoryCacheLock":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.release()


class MemoryCacheBackend:
    """
    In-memory cache backend for development and testing.

    Note: Not suitable for production or multi-process deployments.
    Data is not persisted and not shared between processes.

    Usage:
        cache = MemoryCacheBackend()
        await cache.set("key", "value", ttl=60)
        value = await cache.get("key")
    """

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._store: dict[str, CacheEntry] = {}

    def _ttl_seconds(self, ttl: int | timedelta | None) -> int | None:
        if ttl is None:
            return self.default_ttl
        if isinstance(ttl, timedelta):
            return int(ttl.total_seconds())
        return ttl

    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        expired = [k for k, v in self._store.items() if v.is_expired]
        for key in expired:
            del self._store[key]

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired:
            del self._store[key]
            return None
        return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | timedelta | None = None,
    ) -> bool:
        ttl_seconds = self._ttl_seconds(ttl)
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        self._store[key] = CacheEntry(value=value, expires_at=expires_at)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return False
        if entry.is_expired:
            del self._store[key]
            return False
        return True

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(
        self,
        mapping: dict[str, Any],
        ttl: int | timedelta | None = None,
    ) -> bool:
        for key, value in mapping.items():
            await self.set(key, value, ttl)
        return True

    async def delete_many(self, keys: list[str]) -> int:
        count = 0
        for key in keys:
            if await self.delete(key):
                count += 1
        return count

    async def delete_pattern(self, pattern: str) -> int:
        # Convert Redis pattern to fnmatch pattern
        fnmatch_pattern = pattern.replace("*", "*")
        matching_keys = [k for k in self._store.keys() if fnmatch.fnmatch(k, fnmatch_pattern)]
        return await self.delete_many(matching_keys)

    async def increment(self, key: str, amount: int = 1) -> int:
        value = await self.get(key)
        if value is None:
            value = 0
        new_value = int(value) + amount
        await self.set(key, new_value)
        return new_value

    async def decrement(self, key: str, amount: int = 1) -> int:
        return await self.increment(key, -amount)

    async def ttl(self, key: str) -> int | None:
        entry = self._store.get(key)
        if entry is None or entry.expires_at is None:
            return None
        remaining = (entry.expires_at - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))

    async def expire(self, key: str, ttl: int | timedelta) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return False

        ttl_seconds = self._ttl_seconds(ttl)
        entry.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        return True

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl: int | timedelta | None = None,
    ) -> T:
        value = await self.get(key)
        if value is not None:
            return value

        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value

    async def lock(
        self,
        key: str,
        ttl: int = 30,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> MemoryCacheLock:
        return MemoryCacheLock(key, ttl)

    async def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()
