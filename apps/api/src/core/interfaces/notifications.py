"""
Notification channel protocol.
Implementations: DatabaseChannel, EmailChannel, WebhookChannel, PushChannel
"""
from __future__ import annotations

from typing import Protocol, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class NotificationType(str, Enum):
    """Notification severity/type."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationCategory(str, Enum):
    """Notification categories for user preferences."""
    SYSTEM = "system"           # System alerts, maintenance
    ACCOUNT = "account"         # Account changes, security
    BILLING = "billing"         # Payments, subscriptions
    FEATURE = "feature"         # New features, updates
    SOCIAL = "social"           # Mentions, comments
    MARKETING = "marketing"     # Promotions (user can disable)


@dataclass
class Notification:
    """
    Notification payload.

    Used across all channels - each channel renders appropriately.
    """
    type: NotificationType
    category: NotificationCategory
    title: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    action_url: Optional[str] = None
    action_label: Optional[str] = None  # e.g., "View Details"
    icon: Optional[str] = None  # Icon name or URL
    image_url: Optional[str] = None  # Optional image


@dataclass
class NotificationResult:
    """Result of sending a notification."""
    success: bool
    channel: str
    notification_id: Optional[str] = None
    error: Optional[str] = None
    provider_response: Optional[dict[str, Any]] = None


@dataclass
class BulkNotificationResult:
    """Result of sending bulk notifications."""
    total: int
    sent: int
    failed: int
    results: list[NotificationResult] = field(default_factory=list)


@dataclass
class UserNotificationPreferences:
    """User's notification preferences per category."""
    # Category -> Channel -> Enabled
    # e.g., {"billing": {"in_app": True, "email": True, "webhook": False}}
    preferences: dict[str, dict[str, bool]] = field(default_factory=dict)

    def is_enabled(self, category: str, channel: str) -> bool:
        """Check if a channel is enabled for a category."""
        cat_prefs = self.preferences.get(category, {})
        # Default to True for in_app, False for others
        default = channel == "in_app"
        return cat_prefs.get(channel, default)


class NotificationChannel(Protocol):
    """
    Protocol for notification channels.

    Each channel implements delivery to a specific medium:
    - DatabaseChannel: In-app notifications (stored in DB)
    - EmailChannel: Email notifications
    - WebhookChannel: External webhook delivery
    - PushChannel: Push notifications (mobile/desktop)
    - SMSChannel: SMS notifications
    """

    @property
    def channel_type(self) -> str:
        """Channel identifier (e.g., 'in_app', 'email', 'webhook')."""
        ...

    async def send(
        self,
        user_id: UUID,
        notification: Notification,
    ) -> NotificationResult:
        """
        Send notification to a single user.

        Args:
            user_id: Target user
            notification: Notification payload

        Returns:
            NotificationResult with success/failure
        """
        ...

    async def send_bulk(
        self,
        user_ids: list[UUID],
        notification: Notification,
    ) -> BulkNotificationResult:
        """
        Send notification to multiple users.

        Args:
            user_ids: List of target users
            notification: Notification payload

        Returns:
            BulkNotificationResult with per-user results
        """
        ...

    async def health_check(self) -> bool:
        """Check if the channel is healthy and operational."""
        ...


class NotificationStore(Protocol):
    """
    Protocol for notification persistence.

    Used by DatabaseChannel to store in-app notifications.
    """

    async def create(
        self,
        user_id: UUID,
        notification: Notification,
    ) -> str:
        """Store notification, return ID."""
        ...

    async def get(
        self,
        notification_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get a notification by ID."""
        ...

    async def list_for_user(
        self,
        user_id: UUID,
        read: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List notifications for a user."""
        ...

    async def count_unread(
        self,
        user_id: UUID,
    ) -> int:
        """Count unread notifications for a user."""
        ...

    async def mark_read(
        self,
        notification_id: str,
    ) -> bool:
        """Mark a notification as read."""
        ...

    async def mark_all_read(
        self,
        user_id: UUID,
    ) -> int:
        """Mark all notifications as read. Returns count."""
        ...

    async def delete(
        self,
        notification_id: str,
    ) -> bool:
        """Delete a notification."""
        ...

    async def delete_read(
        self,
        user_id: UUID,
    ) -> int:
        """Delete all read notifications. Returns count."""
        ...


class NotificationPreferencesStore(Protocol):
    """
    Protocol for storing user notification preferences.
    """

    async def get(
        self,
        user_id: UUID,
    ) -> UserNotificationPreferences:
        """Get user's notification preferences."""
        ...

    async def update(
        self,
        user_id: UUID,
        preferences: UserNotificationPreferences,
    ) -> bool:
        """Update user's notification preferences."""
        ...

    async def set_channel(
        self,
        user_id: UUID,
        category: str,
        channel: str,
        enabled: bool,
    ) -> bool:
        """Enable/disable a specific channel for a category."""
        ...
