"""
Enterprise Caching Utilities.

Supports:
- Cache-Aside (lazy loading) - best for read-heavy workloads
- Write-Through (sync writes) - best for data consistency
- Stampede Protection - best for hot keys with expensive computation
- Memoization - best for function result caching
- Tag-Based Invalidation - best for related data updates

Usage:
    # Cache-Aside (most common)
    @cache_aside(key="user:{user_id}", ttl=300)
    async def get_user(user_id: str) -> User: ...

    # Write-Through (cache on write)
    @write_through(key="user:{user_id}", invalidate_patterns=["users:*"])
    async def update_user(user_id: str, data: dict) -> User: ...

    # Stampede Protection (prevent thundering herd)
    @stampede_protect(key="expensive:{id}", lock_ttl=30)
    async def expensive_operation(id: str) -> Result: ...

    # Memoization (short-lived, in-memory fallback)
    @memoize(ttl=60)
    async def compute_stats() -> Stats: ...

    # Tag-based invalidation
    await invalidate_tags(cache, ["user", "profile"])
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
from datetime import timedelta
from enum import Enum
from typing import (
    TypeVar,
    Generic,
    Any,
    Callable,
    Awaitable,
    ParamSpec,
    Optional,
    Union,
)
from dataclasses import dataclass, field

from pydantic import BaseModel
from fastapi import Depends

from src.core.plugins.registry import cache_backends

T = TypeVar("T")
P = ParamSpec("P")


# ============================================================
# CACHE PATTERNS ENUM
# ============================================================

class CachePattern(str, Enum):
    """Available caching patterns."""
    CACHE_ASIDE = "cache_aside"       # Read-through lazy loading
    WRITE_THROUGH = "write_through"   # Sync cache on write
    STAMPEDE = "stampede"             # Lock-protected cache fill
    MEMOIZE = "memoize"               # Function result caching


# ============================================================
# CACHE KEY UTILITIES
# ============================================================

def build_cache_key(
    template: str,
    args: tuple = (),
    kwargs: Optional[dict[str, Any]] = None,
    prefix: str = "",
) -> str:
    """
    Build cache key from template and arguments.

    Template placeholders are replaced with argument values.

    Examples:
        build_cache_key("user:{user_id}", kwargs={"user_id": "123"})
        # Returns: "user:123"

        build_cache_key("items:{0}:{1}", args=("category", "page1"))
        # Returns: "items:category:page1"
    """
    kwargs = kwargs or {}
    key = template

    # Replace positional placeholders {0}, {1}, etc.
    for i, arg in enumerate(args):
        key = key.replace(f"{{{i}}}", str(arg))

    # Replace named placeholders {name}
    for name, value in kwargs.items():
        key = key.replace(f"{{{name}}}", str(value))

    return f"{prefix}{key}" if prefix else key


def hash_args(*args, **kwargs) -> str:
    """
    Create a hash from function arguments.

    Useful for memoization keys when arguments are complex.
    """
    data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(data.encode()).hexdigest()[:12]


def make_key(func: Callable, *args, **kwargs) -> str:
    """
    Generate cache key from function name and arguments.

    Used for automatic key generation in @memoize.
    """
    module = func.__module__.split(".")[-1]
    name = func.__name__
    arg_hash = hash_args(*args, **kwargs)
    return f"{module}:{name}:{arg_hash}"


# ============================================================
# CACHE-ASIDE PATTERN (Lazy Loading)
# ============================================================

def cache_aside(
    key: str,
    ttl: Union[int, timedelta] = 300,
    prefix: str = "",
    skip_none: bool = True,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Cache-aside (lazy loading) decorator.

    Best for:
    - Read-heavy workloads
    - Data that doesn't change frequently
    - Functions with expensive database queries

    How it works:
    1. Check cache for key
    2. If hit, return cached value
    3. If miss, call function, cache result, return

    Args:
        key: Cache key template (e.g., "user:{user_id}")
        ttl: Time-to-live in seconds or timedelta
        prefix: Optional key prefix
        skip_none: Don't cache None results (default: True)

    Example:
        @cache_aside(key="user:{user_id}", ttl=300)
        async def get_user(user_id: str) -> User:
            return await db.get_user(user_id)

        # First call: DB query, cache result
        user = await get_user("123")

        # Second call: Return from cache
        user = await get_user("123")
    """
    ttl_seconds = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = await cache_backends.get_async("redis")
            cache_key = build_cache_key(key, args, kwargs, prefix)

            # Try cache first
            cached = await cache.get(cache_key)
            if cached is not None:
                return cached

            # Cache miss - call function
            result = await func(*args, **kwargs)

            # Cache result (skip None if configured)
            if result is not None or not skip_none:
                await cache.set(cache_key, result, ttl=ttl_seconds)

            return result

        # Attach cache control methods
        wrapper.cache_key = lambda *a, **kw: build_cache_key(key, a, kw, prefix)
        wrapper.invalidate = lambda *a, **kw: _invalidate_key(
            build_cache_key(key, a, kw, prefix)
        )
        return wrapper

    return decorator


# ============================================================
# WRITE-THROUGH PATTERN (Sync Cache on Write)
# ============================================================

def write_through(
    key: str,
    ttl: Union[int, timedelta] = 300,
    prefix: str = "",
    invalidate_patterns: Optional[list[str]] = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Write-through decorator - cache result after write operations.

    Best for:
    - Write operations that return updated data
    - Maintaining cache consistency
    - Update/create functions

    How it works:
    1. Call the write function
    2. Cache the result
    3. Optionally invalidate related cache patterns

    Args:
        key: Cache key template for the result
        ttl: Time-to-live for cached result
        prefix: Optional key prefix
        invalidate_patterns: Patterns to invalidate after write

    Example:
        @write_through(
            key="user:{user_id}",
            invalidate_patterns=["users:list:*"]
        )
        async def update_user(user_id: str, data: dict) -> User:
            return await db.update_user(user_id, data)

        # Updates DB, caches result, invalidates list caches
        user = await update_user("123", {"name": "New Name"})
    """
    ttl_seconds = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = await cache_backends.get_async("redis")

            # Execute write operation
            result = await func(*args, **kwargs)

            # Cache the result
            cache_key = build_cache_key(key, args, kwargs, prefix)
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl_seconds)

            # Invalidate related patterns
            if invalidate_patterns:
                for pattern in invalidate_patterns:
                    await cache.delete_pattern(pattern)

            return result

        return wrapper

    return decorator


# ============================================================
# STAMPEDE PROTECTION (Prevent Thundering Herd)
# ============================================================

def stampede_protect(
    key: str,
    ttl: Union[int, timedelta] = 300,
    lock_ttl: int = 30,
    prefix: str = "",
    skip_none: bool = True,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Stampede protection decorator - prevents thundering herd problem.

    Best for:
    - Hot keys with many concurrent requests
    - Expensive computations that shouldn't run multiple times
    - High-traffic endpoints

    How it works:
    1. Check cache for value
    2. If miss, acquire lock before computing
    3. Re-check cache (another process might have filled it)
    4. Compute, cache, release lock
    5. Other waiters get cached value

    Args:
        key: Cache key template
        ttl: Time-to-live for cached value
        lock_ttl: Lock timeout (should be > computation time)
        prefix: Optional key prefix
        skip_none: Don't cache None results

    Example:
        @stampede_protect(key="expensive:{id}", lock_ttl=60)
        async def expensive_operation(id: str) -> Result:
            # Only one process runs this at a time
            return await compute_expensive_thing(id)
    """
    ttl_seconds = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = await cache_backends.get_async("redis")
            cache_key = build_cache_key(key, args, kwargs, prefix)

            # First check - no lock needed
            cached = await cache.get(cache_key)
            if cached is not None:
                return cached

            # Acquire lock to prevent stampede
            async with await cache.lock(cache_key, ttl=lock_ttl):
                # Double-check after acquiring lock
                cached = await cache.get(cache_key)
                if cached is not None:
                    return cached

                # We're the winner - compute and cache
                result = await func(*args, **kwargs)

                if result is not None or not skip_none:
                    await cache.set(cache_key, result, ttl=ttl_seconds)

                return result

        return wrapper

    return decorator


# ============================================================
# MEMOIZATION (Function Result Caching)
# ============================================================

# In-memory fallback cache for when Redis is unavailable
_memory_cache: dict[str, tuple[Any, float]] = {}
_memory_cache_lock = asyncio.Lock()


def memoize(
    ttl: Union[int, timedelta] = 60,
    key: Optional[str] = None,
    use_memory_fallback: bool = True,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Memoization decorator for caching function results.

    Best for:
    - Pure functions with deterministic output
    - Short-lived caches (stats, aggregations)
    - Functions called frequently with same arguments

    How it works:
    1. Generate key from function name and arguments (or use custom key)
    2. Check cache (Redis, with in-memory fallback)
    3. If miss, compute and cache

    Args:
        ttl: Time-to-live (default 60 seconds)
        key: Custom key template (auto-generated if not provided)
        use_memory_fallback: Use in-memory cache if Redis fails

    Example:
        @memoize(ttl=60)
        async def compute_stats() -> Stats:
            return await db.aggregate_stats()

        # With custom key
        @memoize(ttl=300, key="stats:{period}")
        async def get_period_stats(period: str) -> Stats:
            return await db.get_stats(period)
    """
    ttl_seconds = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Build cache key
            if key:
                cache_key = build_cache_key(key, args, kwargs)
            else:
                cache_key = make_key(func, *args, **kwargs)

            try:
                cache = await cache_backends.get_async("redis")

                # Try Redis cache
                cached = await cache.get(cache_key)
                if cached is not None:
                    return cached

                # Compute
                result = await func(*args, **kwargs)

                # Cache in Redis
                await cache.set(cache_key, result, ttl=ttl_seconds)
                return result

            except Exception:
                if not use_memory_fallback:
                    raise

                # Fallback to in-memory cache
                import time
                now = time.time()

                async with _memory_cache_lock:
                    if cache_key in _memory_cache:
                        value, expires = _memory_cache[cache_key]
                        if expires > now:
                            return value
                        del _memory_cache[cache_key]

                # Compute
                result = await func(*args, **kwargs)

                # Store in memory
                async with _memory_cache_lock:
                    _memory_cache[cache_key] = (result, now + ttl_seconds)

                return result

        # Clear memoization cache
        async def clear():
            if not key:
                # No custom key template, nothing specific to clear
                return
            cache = await cache_backends.get_async("redis")
            # Extract prefix from key template (e.g., "stats:{period}" -> "stats")
            key_prefix = key.split(":")[0] if ":" in key else key
            await cache.delete_pattern(f"{key_prefix}:*")

        wrapper.clear = clear
        return wrapper

    return decorator


# ============================================================
# CACHE INVALIDATION UTILITIES
# ============================================================

async def _invalidate_key(key: str) -> bool:
    """Internal helper to invalidate a single key."""
    cache = await cache_backends.get_async("redis")
    return await cache.delete(key)


async def invalidate_keys(keys: list[str]) -> int:
    """
    Invalidate multiple cache keys.

    Returns count of keys deleted.
    """
    if not keys:
        return 0
    cache = await cache_backends.get_async("redis")
    return await cache.delete_many(keys)


async def invalidate_pattern(pattern: str) -> int:
    """
    Invalidate all keys matching a pattern.

    Example:
        await invalidate_pattern("user:*")      # All user keys
        await invalidate_pattern("*:list:*")    # All list keys
    """
    cache = await cache_backends.get_async("redis")
    return await cache.delete_pattern(pattern)


async def invalidate_tags(tags: list[str], prefix: str = "tag:") -> int:
    """
    Invalidate all keys associated with given tags.

    Tags are stored as sets in Redis, containing the keys.
    This provides efficient tag-based invalidation.

    Example:
        # When caching, associate with tags
        await tag_cache_key("user:123", ["user", "profile"])

        # Later, invalidate all user-related caches
        await invalidate_tags(["user"])
    """
    cache = await cache_backends.get_async("redis")
    total_deleted = 0

    for tag in tags:
        tag_key = f"{prefix}{tag}"
        # Get all keys with this tag
        keys = await cache.get(tag_key) or []
        if keys:
            total_deleted += await cache.delete_many(keys)
            await cache.delete(tag_key)

    return total_deleted


async def tag_cache_key(key: str, tags: list[str], prefix: str = "tag:") -> None:
    """
    Associate a cache key with tags for later invalidation.

    Example:
        await cache.set("user:123", user_data)
        await tag_cache_key("user:123", ["user", "profile", "active"])
    """
    cache = await cache_backends.get_async("redis")

    for tag in tags:
        tag_key = f"{prefix}{tag}"
        existing = await cache.get(tag_key) or []
        if key not in existing:
            existing.append(key)
            await cache.set(tag_key, existing, ttl=86400)  # 24 hour TTL for tags


# ============================================================
# FASTAPI DEPENDENCIES
# ============================================================

async def get_cache():
    """
    FastAPI dependency to get the configured cache backend.

    Usage:
        @router.get("/data")
        async def get_data(cache: CacheBackend = Depends(get_cache)):
            cached = await cache.get("my_key")
            ...
    """
    cache = await cache_backends.get_async("redis")
    # Ensure connected (for Redis)
    if hasattr(cache, "connect"):
        await cache.connect()
    return cache


def cached_response(
    key: str,
    ttl: Union[int, timedelta] = 300,
    prefix: str = "response:",
):
    """
    Factory for route-level response caching dependency.

    Usage:
        @router.get("/expensive")
        async def expensive_endpoint(
            cached: Optional[dict] = Depends(cached_response("expensive", ttl=600))
        ):
            if cached is not None:
                return cached

            result = await compute_expensive()
            return result

    Note: For simpler use, prefer the @cache_aside decorator on service functions.
    """
    ttl_seconds = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl

    async def dependency() -> Optional[Any]:
        cache = await cache_backends.get_async("redis")
        return await cache.get(f"{prefix}{key}")

    return dependency


# ============================================================
# CACHE STATS & MONITORING
# ============================================================

@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    size: int = 0
    memory_mb: float = 0.0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


async def get_cache_stats() -> CacheStats:
    """
    Get cache statistics (Redis-specific).

    Returns basic stats about cache usage.
    """
    cache = await cache_backends.get_async("redis")

    if hasattr(cache, "client"):
        info = await cache.client.info("memory")
        dbsize = await cache.client.dbsize()
        return CacheStats(
            size=dbsize,
            memory_mb=info.get("used_memory", 0) / (1024 * 1024),
        )

    return CacheStats()


# ============================================================
# LEGACY ALIASES (backward compatibility)
# ============================================================

# Common alias
cached = cache_aside
