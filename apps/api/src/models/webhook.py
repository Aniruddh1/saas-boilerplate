"""Webhook model for outbound HTTP notifications."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Webhook(Base, UUIDMixin, TimestampMixin):
    """Webhook configuration for sending events to external URLs."""

    __tablename__ = "webhooks"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))

    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048))
    secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Event types to subscribe to (e.g., ["project.created", "user.updated"])
    events: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    headers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Custom headers

    # Stats
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_count: Mapped[int] = mapped_column(default=0)

    # Auto-disable after N consecutive failures
    max_failures: Mapped[int] = mapped_column(default=5)

    # Relationships
    org: Mapped["Organization"] = relationship(back_populates="webhooks")
    logs: Mapped[list["WebhookLog"]] = relationship(back_populates="webhook", cascade="all, delete-orphan")


class WebhookLog(Base, UUIDMixin):
    """Log of webhook delivery attempts."""

    __tablename__ = "webhook_logs"

    webhook_id: Mapped[UUID] = mapped_column(ForeignKey("webhooks.id", ondelete="CASCADE"))

    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONB)

    # Request details
    request_headers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Response details
    response_status: Mapped[Optional[int]] = mapped_column(nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Retry tracking
    attempt: Mapped[int] = mapped_column(default=1)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    webhook: Mapped["Webhook"] = relationship(back_populates="logs")
