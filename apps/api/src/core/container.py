"""
Dependency injection container.
Centralizes all service instantiation and configuration.
"""

from typing import Any
from dataclasses import dataclass, field

from .interfaces import (
    StorageBackend,
    CacheBackend,
    QueueBackend,
    SearchBackend,
    EmailBackend,
    EventBus,
)
from .plugins.registry import (
    storage_backends,
    cache_backends,
    queue_backends,
    search_backends,
    email_backends,
    event_backends,
)


@dataclass
class Container:
    """
    Dependency injection container.

    Holds all service instances and provides easy access.
    Configure backends via settings, get instances here.

    Example:
    ```python
    from src.core.container import container

    # Get configured storage backend
    storage = container.storage

    # Use it
    await storage.upload("file.txt", data)
    ```
    """

    _config: dict[str, Any] = field(default_factory=dict)
    _instances: dict[str, Any] = field(default_factory=dict)

    # Backend type selections (from config)
    storage_type: str = "local"
    cache_type: str = "redis"
    queue_type: str = "celery"
    search_type: str = "meilisearch"
    email_type: str = "smtp"
    events_type: str = "redis"

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the container from settings."""
        self._config = config

        # Set backend types from config
        backends = config.get("backends", {})
        self.storage_type = backends.get("storage", "local")
        self.cache_type = backends.get("cache", "redis")
        self.queue_type = backends.get("queue", "celery")
        self.search_type = backends.get("search", "meilisearch")
        self.email_type = backends.get("email", "smtp")
        self.events_type = backends.get("events", "redis")

    @property
    def storage(self) -> StorageBackend:
        """Get configured storage backend."""
        if "storage" not in self._instances:
            config = self._config.get("storage", {})
            self._instances["storage"] = storage_backends.get(
                self.storage_type,
                config=config,
            )
        return self._instances["storage"]

    @property
    def cache(self) -> CacheBackend:
        """Get configured cache backend."""
        if "cache" not in self._instances:
            config = self._config.get("cache", {})
            self._instances["cache"] = cache_backends.get(
                self.cache_type,
                config=config,
            )
        return self._instances["cache"]

    @property
    def queue(self) -> QueueBackend:
        """Get configured queue backend."""
        if "queue" not in self._instances:
            config = self._config.get("queue", {})
            self._instances["queue"] = queue_backends.get(
                self.queue_type,
                config=config,
            )
        return self._instances["queue"]

    @property
    def search(self) -> SearchBackend:
        """Get configured search backend."""
        if "search" not in self._instances:
            config = self._config.get("search", {})
            self._instances["search"] = search_backends.get(
                self.search_type,
                config=config,
            )
        return self._instances["search"]

    @property
    def email(self) -> EmailBackend:
        """Get configured email backend."""
        if "email" not in self._instances:
            config = self._config.get("email", {})
            self._instances["email"] = email_backends.get(
                self.email_type,
                config=config,
            )
        return self._instances["email"]

    @property
    def events(self) -> EventBus:
        """Get configured event bus."""
        if "events" not in self._instances:
            config = self._config.get("events", {})
            self._instances["events"] = event_backends.get(
                self.events_type,
                config=config,
            )
        return self._instances["events"]

    def get(self, name: str) -> Any:
        """Get any registered instance by name."""
        return self._instances.get(name)

    def set(self, name: str, instance: Any) -> None:
        """Set a custom instance."""
        self._instances[name] = instance

    def clear(self) -> None:
        """Clear all instances (for testing)."""
        self._instances.clear()

    async def initialize(self) -> None:
        """Initialize all backends that need async setup."""
        # Initialize event bus
        if "events" in self._instances:
            await self.events.start()

    async def shutdown(self) -> None:
        """Shutdown all backends gracefully."""
        if "events" in self._instances:
            await self.events.stop()


# Global container instance
container = Container()


# FastAPI dependency functions
async def get_storage() -> StorageBackend:
    """FastAPI dependency for storage."""
    return container.storage


async def get_cache() -> CacheBackend:
    """FastAPI dependency for cache."""
    return container.cache


async def get_queue() -> QueueBackend:
    """FastAPI dependency for queue."""
    return container.queue


async def get_search() -> SearchBackend:
    """FastAPI dependency for search."""
    return container.search


async def get_email() -> EmailBackend:
    """FastAPI dependency for email."""
    return container.email


async def get_events() -> EventBus:
    """FastAPI dependency for event bus."""
    return container.events
