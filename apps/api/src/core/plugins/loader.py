"""
Plugin discovery and loading utilities.
"""
from __future__ import annotations

from typing import Type
from pathlib import Path
import importlib
import importlib.util
import logging
import sys

from .registry import Plugin, PluginRegistry

logger = logging.getLogger(__name__)


def discover_plugins(
    directory: Path | str,
    base_class: Type[Plugin] = Plugin,
) -> list[Type[Plugin]]:
    """
    Discover plugin classes in a directory.

    Looks for Python files and classes that inherit from base_class.

    Args:
        directory: Path to search for plugins
        base_class: Base class plugins must inherit from
    """
    directory = Path(directory)
    discovered = []

    if not directory.exists():
        logger.warning(f"Plugin directory does not exist: {directory}")
        return discovered

    for file_path in directory.glob("*.py"):
        if file_path.name.startswith("_"):
            continue

        try:
            module_name = f"plugins.{file_path.stem}"

            spec = importlib.util.spec_from_file_location(
                module_name, file_path
            )
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find plugin classes in module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, base_class)
                    and attr is not base_class
                ):
                    discovered.append(attr)
                    logger.debug(f"Discovered plugin: {attr_name}")

        except Exception as e:
            logger.error(f"Error loading plugin from {file_path}: {e}")

    return discovered


def load_plugins(
    registry: PluginRegistry,
    directory: Path | str,
    config: dict[str, dict] | None = None,
) -> list[str]:
    """
    Discover and load plugins into a registry.

    Args:
        registry: Plugin registry to load into
        directory: Directory to search for plugins
        config: Configuration dict keyed by plugin name

    Returns:
        List of loaded plugin names
    """
    config = config or {}
    loaded = []

    plugins = discover_plugins(directory)

    for plugin_cls in plugins:
        try:
            plugin = plugin_cls()
            info = plugin.info

            registry.register_plugin(plugin)

            plugin_config = config.get(info.name, {})
            # Note: actual loading is async, done separately
            loaded.append(info.name)

        except Exception as e:
            logger.error(f"Error registering plugin {plugin_cls}: {e}")

    return loaded


def load_from_entrypoints(
    registry: PluginRegistry,
    group: str,
) -> list[str]:
    """
    Load plugins from setuptools entry points.

    This allows plugins to be installed as separate packages.

    Example pyproject.toml in plugin package:
    ```toml
    [project.entry-points."saas.plugins.storage"]
    s3 = "my_storage_plugin:S3StoragePlugin"
    ```

    Args:
        registry: Plugin registry to load into
        group: Entry point group name (e.g., "saas.plugins.storage")
    """
    loaded = []

    try:
        if sys.version_info >= (3, 10):
            from importlib.metadata import entry_points
            eps = entry_points(group=group)
        else:
            from importlib.metadata import entry_points
            eps = entry_points().get(group, [])

        for ep in eps:
            try:
                plugin_cls = ep.load()
                plugin = plugin_cls()
                registry.register_plugin(plugin)
                loaded.append(plugin.info.name)
                logger.info(f"Loaded plugin from entrypoint: {ep.name}")
            except Exception as e:
                logger.error(f"Error loading plugin {ep.name}: {e}")

    except Exception as e:
        logger.error(f"Error loading entry points for {group}: {e}")

    return loaded
