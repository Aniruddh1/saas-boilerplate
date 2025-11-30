"""
Hook system for lifecycle events.
Allows plugins and extensions to tap into application events.
"""

from .manager import HookManager, Hook, HookPriority
from .decorators import hook, before, after

__all__ = [
    "HookManager",
    "Hook",
    "HookPriority",
    "hook",
    "before",
    "after",
]
