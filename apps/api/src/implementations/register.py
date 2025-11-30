"""
Register all backend implementations with their registries.

Import this module in app startup to register all implementations.
"""

from src.core.plugins.registry import (
    storage_backends,
    cache_backends,
)
from src.core.config import settings


def register_backends() -> None:
    """Register all backend implementations."""

    # ============ Cache Backends ============

    def create_redis_cache(**config):
        from src.implementations.cache.redis import RedisCacheBackend
        return RedisCacheBackend(
            redis_url=config.get("url", str(settings.redis.url)),
            prefix=config.get("prefix", "cache:"),
            default_ttl=config.get("default_ttl", 3600),
        )

    def create_memory_cache(**config):
        from src.implementations.cache.memory import MemoryCacheBackend
        return MemoryCacheBackend(
            default_ttl=config.get("default_ttl", 3600),
        )

    cache_backends.register("redis", create_redis_cache, default=True)
    cache_backends.register("memory", create_memory_cache)

    # ============ Storage Backends ============

    def create_local_storage(**config):
        from src.implementations.storage.local import LocalStorageBackend
        return LocalStorageBackend(
            base_path=config.get("path", settings.storage.local_path),
            base_url=config.get("base_url", "/files"),
        )

    storage_backends.register("local", create_local_storage, default=True)

    # Note: S3 backend can be added here when needed:
    # def create_s3_storage(**config):
    #     from src.implementations.storage.s3 import S3StorageBackend
    #     return S3StorageBackend(
    #         bucket=config.get("bucket", settings.storage.s3_bucket),
    #         region=config.get("region", settings.storage.s3_region),
    #         ...
    #     )
    # storage_backends.register("s3", create_s3_storage)
