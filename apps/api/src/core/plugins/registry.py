"""
Plugin registry for managing extensible components.
"""
from __future__ import annotations

from typing import TypeVar, Generic, Callable, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PluginStatus(str, Enum):
    REGISTERED = "registered"
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginInfo:
    """Plugin metadata."""
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] | None = None


class Plugin(ABC):
    """Base class for plugins."""

    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """Return plugin metadata."""
        ...

    async def on_load(self, config: dict[str, Any]) -> None:
        """Called when plugin is loaded. Override to initialize."""
        pass

    async def on_unload(self) -> None:
        """Called when plugin is unloaded. Override to cleanup."""
        pass

    async def health_check(self) -> bool:
        """Check if plugin is healthy. Override for custom checks."""
        return True


@dataclass
class RegisteredPlugin:
    """Internal plugin registration data."""
    plugin: Plugin
    status: PluginStatus = PluginStatus.REGISTERED
    config: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class PluginRegistry(Generic[T]):
    """
    Generic plugin registry for managing backend implementations.

    Example usage:
    ```python
    # Create registry for storage backends
    storage_registry = PluginRegistry[StorageBackend]("storage")

    # Register implementations
    storage_registry.register("s3", S3StorageBackend)
    storage_registry.register("local", LocalStorageBackend)
    storage_registry.register("gcs", GCSStorageBackend)

    # Get implementation
    storage = storage_registry.get("s3", config={"bucket": "my-bucket"})
    ```
    """

    def __init__(self, name: str):
        self.name = name
        self._factories: dict[str, Callable[..., T]] = {}
        self._instances: dict[str, T] = {}
        self._plugins: dict[str, RegisteredPlugin] = {}
        self._default: str | None = None

    def register(
        self,
        name: str,
        factory: Callable[..., T],
        *,
        default: bool = False,
    ) -> None:
        """
        Register a backend implementation.

        Args:
            name: Unique identifier for this implementation
            factory: Callable that creates the implementation
            default: Set as default implementation
        """
        if name in self._factories:
            logger.warning(f"Overwriting existing {self.name} backend: {name}")

        self._factories[name] = factory

        if default or self._default is None:
            self._default = name

        logger.info(f"Registered {self.name} backend: {name}")

    def register_plugin(self, plugin: Plugin) -> None:
        """Register a full plugin with lifecycle hooks."""
        info = plugin.info
        self._plugins[info.name] = RegisteredPlugin(plugin=plugin)
        logger.info(f"Registered plugin: {info.name} v{info.version}")

    def unregister(self, name: str) -> bool:
        """Unregister a backend."""
        if name in self._factories:
            del self._factories[name]
            if name in self._instances:
                del self._instances[name]
            if name == self._default:
                self._default = next(iter(self._factories), None)
            return True
        return False

    def get(
        self,
        name: str | None = None,
        *,
        config: dict[str, Any] | None = None,
        cached: bool = True,
    ) -> T:
        """
        Get a backend implementation.

        Args:
            name: Backend name (uses default if not specified)
            config: Configuration to pass to factory
            cached: Return cached instance if available
        """
        name = name or self._default

        if name is None:
            raise ValueError(f"No {self.name} backend registered")

        if name not in self._factories:
            available = ", ".join(self._factories.keys())
            raise ValueError(
                f"Unknown {self.name} backend: {name}. "
                f"Available: {available}"
            )

        # Return cached instance if available and requested
        cache_key = f"{name}:{hash(str(config))}" if config else name
        if cached and cache_key in self._instances:
            return self._instances[cache_key]

        # Create new instance
        factory = self._factories[name]
        instance = factory(**(config or {}))

        if cached:
            self._instances[cache_key] = instance

        return instance

    async def get_async(
        self,
        name: str | None = None,
        *,
        config: dict[str, Any] | None = None,
    ) -> T:
        """Get backend with async initialization."""
        instance = self.get(name, config=config, cached=False)

        # Call async init if available
        if hasattr(instance, "initialize"):
            await instance.initialize()

        return instance

    def list(self) -> list[str]:
        """List all registered backend names."""
        return list(self._factories.keys())

    def has(self, name: str) -> bool:
        """Check if backend is registered."""
        return name in self._factories

    @property
    def default(self) -> str | None:
        """Get default backend name."""
        return self._default

    @default.setter
    def default(self, name: str) -> None:
        """Set default backend."""
        if name not in self._factories:
            raise ValueError(f"Unknown {self.name} backend: {name}")
        self._default = name

    async def load_plugin(
        self,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Load and activate a plugin."""
        if name not in self._plugins:
            raise ValueError(f"Plugin not registered: {name}")

        reg = self._plugins[name]
        reg.config = config or {}

        try:
            await reg.plugin.on_load(reg.config)
            reg.status = PluginStatus.ACTIVE
            logger.info(f"Loaded plugin: {name}")
        except Exception as e:
            reg.status = PluginStatus.ERROR
            reg.error = str(e)
            logger.error(f"Failed to load plugin {name}: {e}")
            raise

    async def unload_plugin(self, name: str) -> None:
        """Unload a plugin."""
        if name not in self._plugins:
            return

        reg = self._plugins[name]
        try:
            await reg.plugin.on_unload()
            reg.status = PluginStatus.DISABLED
            logger.info(f"Unloaded plugin: {name}")
        except Exception as e:
            logger.error(f"Error unloading plugin {name}: {e}")

    def get_plugin(self, name: str) -> Plugin | None:
        """Get a registered plugin."""
        if name in self._plugins:
            return self._plugins[name].plugin
        return None

    def list_plugins(self) -> list[PluginInfo]:
        """List all registered plugins."""
        return [reg.plugin.info for reg in self._plugins.values()]


# Global registries for common backends
storage_backends = PluginRegistry[Any]("storage")
cache_backends = PluginRegistry[Any]("cache")
queue_backends = PluginRegistry[Any]("queue")
search_backends = PluginRegistry[Any]("search")
email_backends = PluginRegistry[Any]("email")
event_backends = PluginRegistry[Any]("events")
