"""
Project model.
"""

from uuid import UUID, uuid4
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    """Project model."""

    __tablename__ = "projects"

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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    org: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="projects",
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="project",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Project {self.slug}>"


# Import at bottom
from .org import Organization
from .api_key import APIKey
