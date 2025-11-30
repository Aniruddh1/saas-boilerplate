"""Audit log model for tracking all changes."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin


class AuditLog(Base, UUIDMixin):
    """
    Immutable audit log for tracking all changes in the system.

    Every create/update/delete operation should create an audit log entry.
    """

    __tablename__ = "audit_logs"

    # Who performed the action
    actor_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Denormalized for history
    actor_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    actor_user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # What was affected
    org_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True
    )
    resource_type: Mapped[str] = mapped_column(String(100))  # e.g., "user", "project", "org"
    resource_id: Mapped[str] = mapped_column(String(255))  # UUID or other ID as string

    # What happened
    action: Mapped[str] = mapped_column(String(50))  # "create", "update", "delete", "login", etc.

    # Change details
    changes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {"field": {"old": x, "new": y}}
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Additional context

    # Human-readable summary
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Request context
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    # Relationships
    actor: Mapped[Optional["User"]] = relationship()
    org: Mapped[Optional["Organization"]] = relationship()

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.resource_type}:{self.resource_id}>"
