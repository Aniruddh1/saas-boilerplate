"""
API Key model.
"""

from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
from sqlalchemy import String, ForeignKey, DateTime, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .base import Base, TimestampMixin


class APIKeyType(str, Enum):
    """API key types."""
    MASTER = "master"   # Full access
    SERVER = "server"   # Server-side, most permissions
    CLIENT = "client"   # Client-side, limited permissions


class APIKey(Base, TimestampMixin):
    """API Key model."""

    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Key identification (prefix visible, hash stored)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    key_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    # Metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    key_type: Mapped[APIKeyType] = mapped_column(
        SQLEnum(APIKeyType),
        default=APIKeyType.SERVER,
        nullable=False,
    )

    # Scope
    org_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Permissions
    actions: Mapped[list[str]] = mapped_column(JSONB, default=["*"])
    resources: Mapped[list[str]] = mapped_column(JSONB, default=["*"])

    # Limits
    rate_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Audit
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    use_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    org: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="api_keys",
    )
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="api_keys",
    )
    created_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="api_keys",
    )

    def __repr__(self) -> str:
        return f"<APIKey {self.key_prefix}*** ({self.name})>"

    @property
    def is_expired(self) -> bool:
        """Check if key is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def can_perform(self, action: str, resource: str) -> bool:
        """Check if key can perform action on resource."""
        if self.is_expired:
            return False

        # Check actions
        action_allowed = "*" in self.actions or action in self.actions
        if not action_allowed:
            # Check wildcard patterns
            action_allowed = any(
                a.endswith("*") and action.startswith(a[:-1])
                for a in self.actions
            )

        # Check resources
        resource_allowed = "*" in self.resources or resource in self.resources
        if not resource_allowed:
            resource_allowed = any(
                r.endswith("*") and resource.startswith(r[:-1])
                for r in self.resources
            )

        return action_allowed and resource_allowed


# Import at bottom
from .org import Organization
from .project import Project
from .user import User
