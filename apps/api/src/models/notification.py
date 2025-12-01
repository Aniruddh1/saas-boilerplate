"""
Notification model for in-app notifications.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID, uuid4

from sqlalchemy import String, Text, ForeignKey, Index, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    """
    In-app notification stored in database.

    Supports:
    - Multiple notification types (info, success, warning, error)
    - Categories for user preferences
    - Optional action URLs for click-through
    - Rich data payload for custom rendering
    """

    __tablename__ = "notifications"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Target user
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification type and category
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="info",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="system",
    )

    # Content
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Optional action
    action_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    action_label: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Additional data (JSON)
    data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Read status
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship
    user = relationship("User", back_populates="notifications")

    # Indexes for common queries
    __table_args__ = (
        # User's unread notifications (most common query)
        Index("ix_notifications_user_unread", "user_id", "read_at"),
        # User's notifications by category
        Index("ix_notifications_user_category", "user_id", "category"),
        # Cleanup old read notifications
        Index("ix_notifications_read_at", "read_at"),
    )

    @property
    def is_read(self) -> bool:
        """Check if notification has been read."""
        return self.read_at is not None


class NotificationPreference(Base):
    """
    User notification preferences per category and channel.

    Allows users to control which notifications they receive
    via which channels.
    """

    __tablename__ = "notification_preferences"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Category (e.g., "billing", "system", "marketing")
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Channel (e.g., "in_app", "email", "webhook")
    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Whether this channel is enabled for this category
    enabled: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    # Unique constraint: one preference per user/category/channel combo
    __table_args__ = (
        Index(
            "ix_notification_prefs_unique",
            "user_id", "category", "channel",
            unique=True,
        ),
    )
