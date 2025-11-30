"""
Cache backend protocol.
Implementations: RedisCache, MemoryCache, MemcachedCache
"""
from __future__ import annotations

from typing import Protocol, Any, TypeVar, Callable, Awaitable
from datetime import timedelta


T = TypeVar("T")


class CacheBackend(Protocol):
    """
    Protocol for cache backends.

    Example implementations:
    - RedisCacheBackend: Redis-based caching
    - MemoryCacheBackend: In-memory LRU cache (for testing/dev)
    - MemcachedBackend: Memcached-based caching
    """

    async def get(self, key: str) -> Any | None:
        """Get value by key. Returns None if not found."""
        ...

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | timedelta | None = None,
    ) -> bool:
        """Set value with optional TTL (seconds or timedelta)."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete key. Returns True if deleted."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple keys. Missing keys not included in result."""
        ...

    async def set_many(
        self,
        mapping: dict[str, Any],
        ttl: int | timedelta | None = None,
    ) -> bool:
        """Set multiple key-value pairs."""
        ...

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple keys. Returns count of deleted."""
        ...

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern (e.g., 'user:*'). Returns count."""
        ...

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment integer value. Creates key with amount if not exists."""
        ...

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement integer value."""
        ...

    async def ttl(self, key: str) -> int | None:
        """Get remaining TTL in seconds. None if no TTL or key missing."""
        ...

    async def expire(self, key: str, ttl: int | timedelta) -> bool:
        """Set/update TTL on existing key."""
        ...

    # Cache-aside pattern helper
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl: int | timedelta | None = None,
    ) -> T:
        """Get from cache or call factory and cache result."""
        ...

    # Lock for distributed coordination
    async def lock(
        self,
        key: str,
        ttl: int = 30,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> "CacheLock":
        """Acquire distributed lock."""
        ...


class CacheLock(Protocol):
    """Distributed lock interface."""

    async def acquire(self) -> bool:
        """Acquire the lock."""
        ...

    async def release(self) -> bool:
        """Release the lock."""
        ...

    async def extend(self, additional_time: int) -> bool:
        """Extend lock TTL."""
        ...

    async def __aenter__(self) -> "CacheLock":
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        ...
