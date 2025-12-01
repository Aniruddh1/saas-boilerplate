"""
Database notification channel - stores notifications in the database for in-app display.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete

from src.core.interfaces.notifications import (
    Notification,
    NotificationResult,
    BulkNotificationResult,
)
from src.models.notification import Notification as NotificationModel


class DatabaseNotificationChannel:
    """
    Database notification channel for in-app notifications.

    Stores notifications in the database, allowing users to
    view their notification history in the app.

    Usage:
        channel = DatabaseNotificationChannel(db)

        # Send single notification
        result = await channel.send(user_id, notification)

        # Send to multiple users
        result = await channel.send_bulk(user_ids, notification)
    """

    channel_type = "in_app"

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def send(
        self,
        user_id: UUID,
        notification: Notification,
    ) -> NotificationResult:
        """
        Store notification in database.

        Returns:
            NotificationResult with the notification ID
        """
        try:
            db_notification = NotificationModel(
                user_id=user_id,
                type=notification.type.value,
                category=notification.category.value,
                title=notification.title,
                message=notification.message,
                action_url=notification.action_url,
                action_label=notification.action_label,
                data=notification.data,
            )

            self.db.add(db_notification)
            await self.db.flush()

            return NotificationResult(
                success=True,
                channel=self.channel_type,
                notification_id=str(db_notification.id),
            )

        except Exception as e:
            return NotificationResult(
                success=False,
                channel=self.channel_type,
                error=str(e),
            )

    async def send_bulk(
        self,
        user_ids: list[UUID],
        notification: Notification,
    ) -> BulkNotificationResult:
        """
        Store notification for multiple users.
        """
        results = []
        sent = 0
        failed = 0

        for user_id in user_ids:
            result = await self.send(user_id, notification)
            results.append(result)
            if result.success:
                sent += 1
            else:
                failed += 1

        # Commit all at once
        await self.db.commit()

        return BulkNotificationResult(
            total=len(user_ids),
            sent=sent,
            failed=failed,
            results=results,
        )

    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            await self.db.execute(select(func.count()).select_from(NotificationModel))
            return True
        except Exception:
            return False

    # --- Additional database-specific methods ---

    async def get(self, notification_id: str) -> Optional[NotificationModel]:
        """Get a notification by ID."""
        result = await self.db.execute(
            select(NotificationModel).where(NotificationModel.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: UUID,
        read: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NotificationModel]:
        """List notifications for a user."""
        query = (
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
        )

        # Apply read filter before pagination
        if read is not None:
            if read:
                query = query.where(NotificationModel.read_at.isnot(None))
            else:
                query = query.where(NotificationModel.read_at.is_(None))

        # Apply ordering and pagination
        query = (
            query
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_unread(self, user_id: UUID) -> int:
        """Count unread notifications for a user."""
        result = await self.db.execute(
            select(func.count())
            .select_from(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .where(NotificationModel.read_at.is_(None))
        )
        return result.scalar() or 0

    async def count_total(
        self,
        user_id: UUID,
        read: Optional[bool] = None,
    ) -> int:
        """Count total notifications for a user with optional read filter."""
        query = (
            select(func.count())
            .select_from(NotificationModel)
            .where(NotificationModel.user_id == user_id)
        )

        if read is not None:
            if read:
                query = query.where(NotificationModel.read_at.isnot(None))
            else:
                query = query.where(NotificationModel.read_at.is_(None))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        result = await self.db.execute(
            update(NotificationModel)
            .where(NotificationModel.id == notification_id)
            .where(NotificationModel.read_at.is_(None))
            .values(read_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        result = await self.db.execute(
            update(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .where(NotificationModel.read_at.is_(None))
            .values(read_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount

    async def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification."""
        result = await self.db.execute(
            delete(NotificationModel)
            .where(NotificationModel.id == notification_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def delete_read(self, user_id: UUID) -> int:
        """Delete all read notifications for a user."""
        result = await self.db.execute(
            delete(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .where(NotificationModel.read_at.isnot(None))
        )
        await self.db.commit()
        return result.rowcount
