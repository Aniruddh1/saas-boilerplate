"""
Base model classes and mixins.

Standard mixins for enterprise applications:
- TimestampMixin: created_at, updated_at (always use)
- AuditMixin: created_by, updated_by (for audit trails)
- SoftDeleteMixin: deleted_at, deleted_by (for soft deletes)
- TenantMixin: tenant_id (for multi-tenancy)
- VersionMixin: version (for optimistic locking)
- UUIDMixin: UUID primary key
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID as PyUUID, uuid4
from sqlalchemy import DateTime, Integer, String, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    """Base class for all models."""

    # Common type annotations - all datetimes are timezone-aware
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# ============================================================
# TIMESTAMP MIXINS
# ============================================================

class TimestampMixin:
    """
    Mixin for created_at and updated_at timestamps.

    All timestamps are stored in UTC (timezone-aware).
    Frontend should convert to user's local timezone for display.

    Usage:
        class MyModel(Base, TimestampMixin):
            __tablename__ = "my_table"
            ...
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AuditMixin:
    """
    Mixin for tracking who created/updated records.

    Use with TimestampMixin for complete audit trail:
    - WHEN: created_at, updated_at (from TimestampMixin)
    - WHO: created_by, updated_by (from AuditMixin)

    Usage:
        class MyModel(Base, TimestampMixin, AuditMixin):
            __tablename__ = "my_table"
            ...

    Note: updated_by must be set manually in your service layer
    since SQLAlchemy can't automatically know the current user.
    """

    created_by: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_by: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


# ============================================================
# SOFT DELETE MIXIN
# ============================================================

class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.

    Instead of hard deleting, records are marked as deleted.

    Usage:
        class MyModel(Base, SoftDeleteMixin):
            ...

        # Soft delete
        record.deleted_at = datetime.utcnow()
        record.deleted_by = current_user_id

        # Query non-deleted
        query.filter(MyModel.deleted_at.is_(None))
    """

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,  # Index for efficient filtering
    )
    deleted_by: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return self.deleted_at is not None


# ============================================================
# MULTI-TENANCY MIXIN
# ============================================================

class TenantMixin:
    """
    Mixin for multi-tenant data isolation.

    Every query should filter by tenant_id to ensure
    data isolation between tenants.

    Usage:
        class MyModel(Base, TenantMixin):
            ...

        # Always filter by tenant
        query.filter(MyModel.tenant_id == current_tenant_id)

    Note: Consider using SQLAlchemy events or a base query
    class to automatically apply tenant filters.
    """

    tenant_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )


# ============================================================
# VERSION MIXIN (Optimistic Locking)
# ============================================================

class VersionMixin:
    """
    Mixin for optimistic locking.

    Prevents lost updates when multiple users edit the same record.
    The version is incremented on each update.

    Usage:
        class MyModel(Base, VersionMixin):
            ...

        # When updating, check version matches
        result = await db.execute(
            update(MyModel)
            .where(MyModel.id == record_id)
            .where(MyModel.version == expected_version)
            .values(data, version=MyModel.version + 1)
        )
        if result.rowcount == 0:
            raise ConflictError("Record was modified by another user")

    API pattern:
        PUT /items/123
        Headers: If-Match: "5"  (version number)

        Response 409 Conflict if version mismatch
    """

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )


# ============================================================
# PRIMARY KEY MIXIN
# ============================================================

class UUIDMixin:
    """
    Mixin for UUID primary key.

    Uses UUID v4 (random) for primary keys.
    Better for distributed systems than auto-increment.

    Usage:
        class MyModel(Base, UUIDMixin):
            __tablename__ = "my_table"
            # No need to define id column
    """

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


# ============================================================
# COMBINED MIXINS (Convenience)
# ============================================================

class StandardMixin(UUIDMixin, TimestampMixin):
    """
    Standard mixin combining UUID + timestamps.

    Use for most models that need basic tracking.

    Provides:
        - id: UUID primary key
        - created_at: When created (UTC)
        - updated_at: When last modified (UTC)
    """
    pass


class AuditedMixin(UUIDMixin, TimestampMixin, AuditMixin):
    """
    Full audit mixin with UUID + timestamps + user tracking.

    Use for models where you need to know WHO made changes.

    Provides:
        - id: UUID primary key
        - created_at, updated_at: Timestamps (UTC)
        - created_by, updated_by: User references
    """
    pass


class TenantAuditedMixin(UUIDMixin, TimestampMixin, AuditMixin, TenantMixin):
    """
    Full mixin for multi-tenant audited records.

    Provides:
        - id: UUID primary key
        - tenant_id: Tenant isolation
        - created_at, updated_at: Timestamps (UTC)
        - created_by, updated_by: User references
    """
    pass
