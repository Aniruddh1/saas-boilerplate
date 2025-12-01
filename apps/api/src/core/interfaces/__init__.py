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
from .notifications import (
    NotificationChannel,
    NotificationStore,
    NotificationPreferencesStore,
    Notification,
    NotificationResult,
    BulkNotificationResult,
    NotificationType,
    NotificationCategory,
    UserNotificationPreferences,
)

__all__ = [
    "StorageBackend",
    "CacheBackend",
    "QueueBackend",
    "SearchBackend",
    "EmailBackend",
    "EventBus",
    # Notifications
    "NotificationChannel",
    "NotificationStore",
    "NotificationPreferencesStore",
    "Notification",
    "NotificationResult",
    "BulkNotificationResult",
    "NotificationType",
    "NotificationCategory",
    "UserNotificationPreferences",
]
