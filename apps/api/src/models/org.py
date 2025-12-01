"""
Organization models.
"""

from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
from sqlalchemy import String, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .base import Base, TimestampMixin


class OrgRole(str, Enum):
    """Organization member roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# Role hierarchy (higher number = more permissions)
ROLE_LEVELS = {
    OrgRole.VIEWER: 10,
    OrgRole.MEMBER: 20,
    OrgRole.ADMIN: 30,
    OrgRole.OWNER: 40,
}


class Organization(Base, TimestampMixin):
    """Organization model."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Billing
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan: Mapped[str] = mapped_column(String(50), default="free")

    # Limits
    max_members: Mapped[int] = mapped_column(Integer, default=5)
    max_projects: Mapped[int] = mapped_column(Integer, default=3)

    # Relationships
    members: Mapped[list["OrgMember"]] = relationship(
        "OrgMember",
        back_populates="org",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="org",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="org",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    webhooks: Mapped[list["Webhook"]] = relationship(
        "Webhook",
        back_populates="org",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization {self.slug}>"


class OrgMember(Base, TimestampMixin):
    """Organization membership."""

    __tablename__ = "org_members"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[OrgRole] = mapped_column(
        SQLEnum(OrgRole),
        default=OrgRole.MEMBER,
        nullable=False,
    )

    # Relationships
    org: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="org_memberships",
    )

    def __repr__(self) -> str:
        return f"<OrgMember org={self.org_id} user={self.user_id} role={self.role}>"

    @property
    def role_level(self) -> int:
        """Get numeric role level for comparison."""
        return ROLE_LEVELS.get(self.role, 0)


# Import at bottom to avoid circular imports
from .user import User
from .project import Project
from .api_key import APIKey
from .webhook import Webhook
