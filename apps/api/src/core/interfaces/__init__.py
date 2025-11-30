"""
Core interfaces (protocols) for extensibility.
All backends must implement these protocols to be swappable.
"""

from .storage import StorageBackend
from .cache import CacheBackend
from .queue import QueueBackend
from .search import SearchBackend
from .email import EmailBackend
from .events import EventBus

__all__ = [
    "StorageBackend",
    "CacheBackend",
    "QueueBackend",
    "SearchBackend",
    "EmailBackend",
    "EventBus",
]
