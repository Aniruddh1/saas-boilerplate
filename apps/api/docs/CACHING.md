# Caching System

Enterprise-grade caching utilities with progressive complexity, supporting cache-aside, write-through, stampede protection, and memoization patterns.

## Overview

| Level | Complexity | Use Case |
|-------|------------|----------|
| 1 | Simple | `@cache_aside` decorator |
| 2 | Write ops | `@write_through` with invalidation |
| 3 | High traffic | `@stampede_protect` for hot keys |
| 4 | Functions | `@memoize` for pure functions |
| 5 | Advanced | Tag-based invalidation |

## Quick Start

### Level 1: Cache-Aside (Lazy Loading)

Best for read-heavy workloads with infrequent updates.

```python
from src.utils.caching import cache_aside

@cache_aside(key="user:{user_id}", ttl=300)
async def get_user(user_id: str) -> User:
    """Cached for 5 minutes."""
    return await db.get_user(user_id)

# First call: DB query, cache result
user = await get_user("123")

# Second call: Return from cache (no DB query)
user = await get_user("123")

# Manual invalidation
await get_user.invalidate("123")
```

### Level 2: Write-Through (Cache on Write)

Best for write operations that need consistent caching.

```python
from src.utils.caching import write_through

@write_through(
    key="user:{user_id}",
    invalidate_patterns=["users:list:*"]
)
async def update_user(user_id: str, data: dict) -> User:
    """Updates DB, caches result, invalidates list caches."""
    return await db.update_user(user_id, data)

# Updates user, caches new data, invalidates any list caches
user = await update_user("123", {"name": "New Name"})
```

### Level 3: Stampede Protection (Prevent Thundering Herd)

Best for hot keys with expensive computations and high concurrent traffic.

```python
from src.utils.caching import stampede_protect

@stampede_protect(key="dashboard:stats", lock_ttl=60)
async def get_dashboard_stats() -> Stats:
    """Only one process computes at a time."""
    return await compute_expensive_stats()

# 100 concurrent requests hit this endpoint:
# - First request acquires lock, computes stats
# - Other 99 wait for lock, then get cached result
```

### Level 4: Memoization (Function Results)

Best for pure functions with deterministic output.

```python
from src.utils.caching import memoize

@memoize(ttl=60)
async def compute_analytics() -> Analytics:
    """Cached for 60 seconds with auto-generated key."""
    return await db.aggregate_analytics()

# With custom key template
@memoize(ttl=300, key="report:{period}:{region}")
async def get_report(period: str, region: str) -> Report:
    return await generate_report(period, region)

# Clear memoized values
await get_report.clear()
```

### Level 5: Tag-Based Invalidation

Best for invalidating related caches efficiently.

```python
from src.utils.caching import tag_cache_key, invalidate_tags, get_cache

@router.get("/users/{user_id}")
async def get_user(user_id: str, cache = Depends(get_cache)):
    user = await fetch_user(user_id)

    # Cache with tags
    cache_key = f"user:{user_id}"
    await cache.set(cache_key, user, ttl=300)
    await tag_cache_key(cache_key, ["user", "profile", f"tenant:{user.tenant_id}"])

    return user

@router.put("/users/{user_id}")
async def update_user(user_id: str):
    await db.update_user(user_id, data)

    # Invalidate all user-related caches
    await invalidate_tags(["user"])
```

## Architecture

```
src/utils/caching.py          # All caching utilities
src/core/interfaces/cache.py  # CacheBackend protocol
src/implementations/cache/
├── redis.py                  # Redis backend
└── memory.py                 # In-memory backend (dev/testing)
```

## Configuration

```env
# Cache backend: redis (default) or memory
CACHE_BACKEND=redis

# Redis connection
REDIS_URL=redis://localhost:6379/0

# Default TTL in seconds
CACHE_DEFAULT_TTL=300
```

## Cache Key Patterns

Keys are built from templates with placeholder replacement:

```python
from src.utils.caching import build_cache_key

# Named placeholders
key = build_cache_key("user:{user_id}", kwargs={"user_id": "123"})
# Result: "user:123"

# Positional placeholders
key = build_cache_key("items:{0}:{1}", args=("category", "page1"))
# Result: "items:category:page1"

# With prefix
key = build_cache_key("user:{id}", kwargs={"id": "123"}, prefix="v2:")
# Result: "v2:user:123"
```

## FastAPI Dependencies

```python
from src.utils.caching import get_cache, cached_response

# Direct cache access
@router.get("/data")
async def get_data(cache = Depends(get_cache)):
    # Manual cache operations
    cached = await cache.get("my_key")
    if cached:
        return cached

    result = await expensive_operation()
    await cache.set("my_key", result, ttl=300)
    return result

# Response-level caching
@router.get("/expensive")
async def expensive_endpoint(
    cached = Depends(cached_response("expensive", ttl=600))
):
    if cached is not None:
        return cached

    result = await compute_expensive()
    # Note: You'd need to cache the result manually
    return result
```

## Cache Invalidation Strategies

### Single Key

```python
from src.utils.caching import _invalidate_key

await _invalidate_key("user:123")
```

### Multiple Keys

```python
from src.utils.caching import invalidate_keys

await invalidate_keys(["user:123", "user:456", "user:789"])
```

### Pattern-Based

```python
from src.utils.caching import invalidate_pattern

# All user keys
await invalidate_pattern("user:*")

# All list keys for any resource
await invalidate_pattern("*:list:*")
```

### Tag-Based

```python
from src.utils.caching import tag_cache_key, invalidate_tags

# Associate keys with tags
await tag_cache_key("user:123", ["user", "profile"])
await tag_cache_key("user:456", ["user", "profile"])

# Invalidate all keys with "user" tag
await invalidate_tags(["user"])
```

## Monitoring

```python
from src.utils.caching import get_cache_stats

stats = await get_cache_stats()
print(f"Hit rate: {stats.hit_rate:.2%}")
print(f"Cache size: {stats.size} keys")
print(f"Memory: {stats.memory_mb:.2f} MB")
```

## Pattern Selection Guide

| Pattern | Use When | TTL | Example |
|---------|----------|-----|---------|
| `cache_aside` | Read-heavy, data rarely changes | 5-60 min | User profiles |
| `write_through` | Write ops need cache consistency | 5-60 min | User updates |
| `stampede_protect` | Hot keys, expensive computation | 1-5 min | Dashboard stats |
| `memoize` | Pure functions, short-lived | 30-120 sec | Aggregations |

## Best Practices

1. **Start simple** - Use `@cache_aside` for most cases
2. **Set appropriate TTLs** - Balance freshness vs performance
3. **Use meaningful key templates** - `user:{user_id}` not `key:{id}`
4. **Invalidate on writes** - Use `invalidate_patterns` in `@write_through`
5. **Monitor hit rates** - Tune TTLs based on cache effectiveness
6. **Handle cache failures gracefully** - Memoize has in-memory fallback
7. **Don't cache everything** - Only cache expensive or frequently accessed data

## Testing

Use memory backend for tests:

```python
import pytest
from src.utils.caching import cache_aside

# In conftest.py, override cache backend to memory
@pytest.fixture(autouse=True)
def use_memory_cache(monkeypatch):
    # Configure memory backend for tests
    pass

async def test_cached_function():
    @cache_aside(key="test:{id}", ttl=60)
    async def get_item(id: str):
        return {"id": id}

    result = await get_item("123")
    assert result["id"] == "123"

    # Verify caching works
    result2 = await get_item("123")
    assert result2 == result
```
