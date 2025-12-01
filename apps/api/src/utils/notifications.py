"""
Enterprise Notification Utilities.

Supports:
- Single notification - one user, one or more channels
- Multi-channel - send via multiple channels simultaneously
- Broadcast - send to many users at once
- Targeted - send to users matching a filter
- Preference-aware - respect user notification preferences

Usage:
    # Single notification
    await notifier.notify(
        user_id,
        notification,
        channels=["in_app", "email"],
    )

    # Broadcast to many users
    await notifier.broadcast(
        user_ids,
        notification,
        channels=["in_app"],
    )

    # Respect user preferences
    await notifier.notify_preferred(
        user_id,
        notification,
        category="billing",
    )
"""

from __future__ import annotations

import asyncio
from uuid import UUID
from typing import Optional, Sequence
from dataclasses import dataclass, field

from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.interfaces.notifications import (
    Notification,
    NotificationType,
    NotificationCategory,
    NotificationChannel,
    NotificationResult,
    BulkNotificationResult,
    UserNotificationPreferences,
)
from src.api.dependencies.database import get_db


# ============================================================
# NOTIFICATION SCHEMAS (for API responses)
# ============================================================

class NotificationResponse(BaseModel):
    """Notification response for API."""
    id: str
    type: str
    category: str
    title: str
    message: str
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    data: dict = {}
    read_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    """Create notification request."""
    type: str = "info"
    category: str = "system"
    title: str
    message: str
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    data: dict = {}


class BroadcastRequest(BaseModel):
    """Broadcast notification request."""
    user_ids: list[str]
    notification: NotificationCreate
    channels: list[str] = ["in_app"]


class NotifyResult(BaseModel):
    """Result of notification send."""
    success: bool
    channels: dict[str, bool]  # channel -> success
    errors: dict[str, str] = {}  # channel -> error message


class BroadcastResult(BaseModel):
    """Result of broadcast notification."""
    total_users: int
    successful: int
    failed: int
    channel_results: dict[str, dict] = {}  # channel -> {sent, failed}


# ============================================================
# NOTIFIER CLASS
# ============================================================

class Notifier:
    """
    Multi-channel notification manager.

    Similar to Paginator and JobManager, provides a unified interface
    with multiple patterns for different use cases.

    Usage:
        notifier = Notifier(channels)

        # Simple notification
        await notifier.notify(user_id, notification)

        # Multi-channel
        await notifier.notify(
            user_id,
            notification,
            channels=["in_app", "email"],
        )

        # Broadcast
        await notifier.broadcast(user_ids, notification)

        # With user preferences
        await notifier.notify_preferred(
            user_id,
            notification,
            category="billing",
        )
    """

    def __init__(
        self,
        channels: dict[str, NotificationChannel],
        preferences_store: Optional[object] = None,
    ):
        """
        Initialize notifier.

        Args:
            channels: Dict of channel_name -> channel instance
            preferences_store: Optional store for user preferences
        """
        self.channels = channels
        self.preferences_store = preferences_store

    # --- Single Notification Pattern ---

    async def notify(
        self,
        user_id: UUID,
        notification: Notification,
        channels: Optional[list[str]] = None,
    ) -> NotifyResult:
        """
        Send notification to a single user via one or more channels.

        Best for:
        - Account notifications
        - Transaction alerts
        - System messages

        Args:
            user_id: Target user
            notification: Notification payload
            channels: List of channels to use (default: ["in_app"])

        Returns:
            NotifyResult with per-channel results

        Example:
            result = await notifier.notify(
                user_id,
                Notification(
                    type=NotificationType.SUCCESS,
                    category=NotificationCategory.BILLING,
                    title="Payment received",
                    message="Your payment of $99 was successful",
                    action_url="/billing/history",
                ),
                channels=["in_app", "email"],
            )
        """
        channels = channels or ["in_app"]
        channel_results = {}
        errors = {}

        for channel_name in channels:
            channel = self.channels.get(channel_name)
            if not channel:
                errors[channel_name] = f"Channel not configured: {channel_name}"
                channel_results[channel_name] = False
                continue

            result = await channel.send(user_id, notification)
            channel_results[channel_name] = result.success
            if not result.success and result.error:
                errors[channel_name] = result.error

        return NotifyResult(
            success=any(channel_results.values()),
            channels=channel_results,
            errors=errors,
        )

    # --- Broadcast Pattern ---

    async def broadcast(
        self,
        user_ids: Sequence[UUID],
        notification: Notification,
        channels: Optional[list[str]] = None,
    ) -> BroadcastResult:
        """
        Send notification to multiple users.

        Best for:
        - System announcements
        - Feature updates
        - Marketing (with user consent)

        Args:
            user_ids: List of target users
            notification: Notification payload
            channels: Channels to use

        Returns:
            BroadcastResult with aggregated results

        Example:
            result = await notifier.broadcast(
                all_user_ids,
                Notification(
                    type=NotificationType.INFO,
                    category=NotificationCategory.SYSTEM,
                    title="Scheduled Maintenance",
                    message="We'll be performing maintenance tonight",
                ),
            )
        """
        channels = channels or ["in_app"]
        channel_results = {}
        total_success = 0
        total_failed = 0

        for channel_name in channels:
            channel = self.channels.get(channel_name)
            if not channel:
                channel_results[channel_name] = {
                    "sent": 0,
                    "failed": len(user_ids),
                    "error": f"Channel not configured: {channel_name}",
                }
                total_failed += len(user_ids)
                continue

            result = await channel.send_bulk(list(user_ids), notification)
            channel_results[channel_name] = {
                "sent": result.sent,
                "failed": result.failed,
            }
            total_success += result.sent
            total_failed += result.failed

        return BroadcastResult(
            total_users=len(user_ids),
            successful=total_success // len(channels) if channels else 0,
            failed=total_failed // len(channels) if channels else 0,
            channel_results=channel_results,
        )

    # --- Preference-Aware Pattern ---

    async def notify_preferred(
        self,
        user_id: UUID,
        notification: Notification,
        category: Optional[str] = None,
    ) -> NotifyResult:
        """
        Send notification respecting user preferences.

        Best for:
        - User-configurable notifications
        - Marketing emails (opt-in/out)
        - Non-critical alerts

        Args:
            user_id: Target user
            notification: Notification payload
            category: Override notification category for preference lookup

        Returns:
            NotifyResult

        Example:
            # User has preferences:
            # - billing: {"in_app": True, "email": True}
            # - marketing: {"in_app": True, "email": False}

            await notifier.notify_preferred(
                user_id,
                notification,
                category="marketing",
            )
            # Only sends to in_app, skips email
        """
        category = category or notification.category.value

        # Get user preferences
        enabled_channels = []
        if self.preferences_store:
            prefs = await self.preferences_store.get(user_id)
            for channel_name in self.channels:
                if prefs.is_enabled(category, channel_name):
                    enabled_channels.append(channel_name)
        else:
            # Default: all channels enabled
            enabled_channels = list(self.channels.keys())

        if not enabled_channels:
            return NotifyResult(
                success=False,
                channels={},
                errors={"all": "No channels enabled for this category"},
            )

        return await self.notify(user_id, notification, channels=enabled_channels)

    # --- Parallel Multi-Channel Pattern ---

    async def notify_parallel(
        self,
        user_id: UUID,
        notification: Notification,
        channels: Optional[list[str]] = None,
    ) -> NotifyResult:
        """
        Send notification to all channels in parallel.

        Best for:
        - Time-sensitive notifications
        - High-priority alerts
        - When channel latency varies

        Example:
            # Send to all channels simultaneously
            result = await notifier.notify_parallel(
                user_id,
                urgent_notification,
                channels=["in_app", "email", "webhook"],
            )
        """
        channels = channels or list(self.channels.keys())
        tasks = []
        channel_names = []

        for channel_name in channels:
            channel = self.channels.get(channel_name)
            if channel:
                tasks.append(channel.send(user_id, notification))
                channel_names.append(channel_name)

        if not tasks:
            return NotifyResult(
                success=False,
                channels={},
                errors={"all": "No valid channels found"},
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        channel_results = {}
        errors = {}

        for channel_name, result in zip(channel_names, results):
            if isinstance(result, Exception):
                channel_results[channel_name] = False
                errors[channel_name] = str(result)
            else:
                channel_results[channel_name] = result.success
                if not result.success and result.error:
                    errors[channel_name] = result.error

        return NotifyResult(
            success=any(channel_results.values()),
            channels=channel_results,
            errors=errors,
        )

    # --- Health Check ---

    async def health_check(self) -> dict[str, bool]:
        """Check health of all channels."""
        results = {}
        for channel_name, channel in self.channels.items():
            try:
                results[channel_name] = await channel.health_check()
            except Exception:
                results[channel_name] = False
        return results


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_notification(
    title: str,
    message: str,
    type: str = "info",
    category: str = "system",
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
    data: Optional[dict] = None,
) -> Notification:
    """
    Helper to create a notification.

    Example:
        notification = create_notification(
            title="Welcome!",
            message="Thanks for signing up",
            type="success",
            action_url="/onboarding",
        )
    """
    return Notification(
        type=NotificationType(type),
        category=NotificationCategory(category),
        title=title,
        message=message,
        action_url=action_url,
        action_label=action_label,
        data=data or {},
    )


# ============================================================
# FASTAPI DEPENDENCIES
# ============================================================

async def get_notifier(
    db: AsyncSession = Depends(get_db),
) -> Notifier:
    """
    FastAPI dependency to get the configured notifier.

    Usage:
        @router.post("/notify")
        async def send_notification(
            data: NotificationCreate,
            notifier: Notifier = Depends(get_notifier),
        ):
            result = await notifier.notify(...)
    """
    from src.implementations.notifications.database import DatabaseNotificationChannel

    # Create channels
    channels = {
        "in_app": DatabaseNotificationChannel(db),
        # Add other channels as configured
    }

    return Notifier(channels)


async def get_database_channel(
    db: AsyncSession = Depends(get_db),
) -> "DatabaseNotificationChannel":
    """Get the database notification channel directly."""
    from src.implementations.notifications.database import DatabaseNotificationChannel
    return DatabaseNotificationChannel(db)
