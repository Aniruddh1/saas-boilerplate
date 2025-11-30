"""
Plugin system for extensibility.
Allows registering and loading plugins at runtime.
"""

from .registry import PluginRegistry, Plugin, PluginInfo
from .loader import load_plugins, discover_plugins

__all__ = [
    "PluginRegistry",
    "Plugin",
    "PluginInfo",
    "load_plugins",
    "discover_plugins",
]
