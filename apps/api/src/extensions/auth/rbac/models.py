"""
RBAC Models - Roles, Permissions, and Assignments.

These models implement a flexible RBAC system with:
- Roles with hierarchical levels
- Permissions as resource:action pairs
- Role assignments with optional scoping
- Multi-tenant support

Usage:
    # Create roles
    admin_role = Role(name="admin", level=100)
    editor_role = Role(name="editor", level=50)

    # Create permissions
    perm = Permission(resource="posts", action="create")

    # Assign role to user
    assignment = UserRole(user_id=user.id, role_id=role.id)
"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, Integer, ForeignKey, DateTime, UniqueConstraint, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from src.models.base import Base, TimestampMixin


# Many-to-many relationship between Role and Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", PGUUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base, TimestampMixin):
    """
    Role definition.

    Roles group permissions together and can be assigned to users.
    The level field enables role hierarchy (higher = more privileged).
    """

    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Role hierarchy level (higher = more privileged)
    # e.g., viewer=10, editor=50, admin=100
    level: Mapped[int] = mapped_column(Integer, default=0)

    # Multi-tenant support (optional)
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.organization_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )
    user_assignments: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class Permission(Base, TimestampMixin):
    """
    Permission definition.

    Permissions are defined as resource:action pairs.
    Conditions can specify additional ABAC-style checks.

    Examples:
        Permission(resource="posts", action="create")
        Permission(resource="posts", action="delete", conditions={"own_only": True})
        Permission(resource="transactions", action="approve", conditions={"max_amount": 10000})
    """

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permission_resource_action"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    resource: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ABAC-style conditions (optional)
    # e.g., {"max_amount": 10000, "own_only": True}
    conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin",
    )

    @property
    def permission_string(self) -> str:
        """Get permission as 'resource:action' string."""
        return f"{self.resource}:{self.action}"

    def __repr__(self) -> str:
        return f"<Permission {self.resource}:{self.action}>"


class UserRole(Base, TimestampMixin):
    """
    User role assignment.

    Links a user to a role with optional scoping.
    Scoping allows limiting a role to specific resources.

    Examples:
        # Global role
        UserRole(user_id=user.id, role_id=admin.id)

        # Scoped to an entity
        UserRole(user_id=user.id, role_id=manager.id, scope_type="entity", scope_id=entity.id)

        # Temporary role
        UserRole(user_id=user.id, role_id=approver.id, valid_until=datetime(2024, 12, 31))
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id", name="uq_user_role_scope"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional scoping
    scope_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g., "entity", "department", "project"
    scope_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )  # ID of the scoped resource

    # Validity period (for temporary access)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Who granted this role
    granted_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="user_assignments")

    @property
    def is_valid(self) -> bool:
        """Check if this role assignment is currently valid."""
        now = datetime.utcnow()
        if self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        return True

    def __repr__(self) -> str:
        scope = f" ({self.scope_type}:{self.scope_id})" if self.scope_type else ""
        return f"<UserRole user={self.user_id} role={self.role_id}{scope}>"
