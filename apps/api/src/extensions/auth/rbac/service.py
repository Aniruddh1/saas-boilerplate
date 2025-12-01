"""
RBAC Service - Manage roles, permissions, and assignments.

Usage:
    service = RBACService(db)

    # Create a role with permissions
    role = await service.create_role(
        name="editor",
        permissions=["posts:create", "posts:update", "posts:delete"]
    )

    # Assign role to user
    await service.assign_role(user_id, role.id)

    # Check if user has permission
    has_perm = await service.has_permission(user_id, "posts:create")
"""

from typing import Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Role, Permission, UserRole


class RBACService:
    """
    Service for managing RBAC roles, permissions, and assignments.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # ROLE MANAGEMENT
    # ============================================================

    async def create_role(
        self,
        name: str,
        permissions: list[str] | None = None,
        description: str | None = None,
        level: int = 0,
        organization_id: UUID | None = None,
    ) -> Role:
        """
        Create a new role with optional permissions.

        Args:
            name: Unique role name
            permissions: List of permission strings (e.g., ["posts:create", "posts:update"])
            description: Role description
            level: Hierarchy level (higher = more privileged)
            organization_id: Optional tenant ID for multi-tenant

        Returns:
            Created Role
        """
        role = Role(
            name=name,
            description=description,
            level=level,
            organization_id=organization_id,
        )
        self.db.add(role)
        await self.db.flush()

        # Add permissions
        if permissions:
            for perm_str in permissions:
                perm = await self.get_or_create_permission(perm_str)
                role.permissions.append(perm)

        await self.db.flush()
        return role

    async def get_role(self, role_id: UUID) -> Role | None:
        """Get role by ID."""
        result = await self.db.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> Role | None:
        """Get role by name."""
        result = await self.db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def list_roles(
        self,
        organization_id: UUID | None = None,
    ) -> list[Role]:
        """List all roles, optionally filtered by organization."""
        query = select(Role)
        if organization_id:
            query = query.where(Role.organization_id == organization_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_role(
        self,
        role_id: UUID,
        name: str | None = None,
        description: str | None = None,
        level: int | None = None,
    ) -> Role | None:
        """Update role properties."""
        role = await self.get_role(role_id)
        if not role:
            return None

        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        if level is not None:
            role.level = level

        await self.db.flush()
        return role

    async def delete_role(self, role_id: UUID) -> bool:
        """Delete a role."""
        role = await self.get_role(role_id)
        if not role:
            return False

        await self.db.delete(role)
        await self.db.flush()
        return True

    async def add_permission_to_role(
        self,
        role_id: UUID,
        permission: str,
    ) -> Role | None:
        """Add a permission to a role."""
        role = await self.get_role(role_id)
        if not role:
            return None

        perm = await self.get_or_create_permission(permission)
        if perm not in role.permissions:
            role.permissions.append(perm)
            await self.db.flush()

        return role

    async def remove_permission_from_role(
        self,
        role_id: UUID,
        permission: str,
    ) -> Role | None:
        """Remove a permission from a role."""
        role = await self.get_role(role_id)
        if not role:
            return None

        # Find and remove permission
        for perm in role.permissions:
            if perm.permission_string == permission:
                role.permissions.remove(perm)
                break

        await self.db.flush()
        return role

    # ============================================================
    # PERMISSION MANAGEMENT
    # ============================================================

    async def get_or_create_permission(
        self,
        permission_string: str,
        conditions: dict | None = None,
    ) -> Permission:
        """
        Get or create a permission.

        Args:
            permission_string: Permission in "resource:action" format
            conditions: Optional ABAC conditions

        Returns:
            Permission object
        """
        if ":" in permission_string:
            resource, action = permission_string.split(":", 1)
        else:
            resource = permission_string
            action = "*"

        # Try to find existing
        query = select(Permission).where(
            Permission.resource == resource,
            Permission.action == action,
        )
        result = await self.db.execute(query)
        perm = result.scalar_one_or_none()

        if not perm:
            perm = Permission(
                resource=resource,
                action=action,
                conditions=conditions,
            )
            self.db.add(perm)
            await self.db.flush()

        return perm

    async def list_permissions(self) -> list[Permission]:
        """List all permissions."""
        result = await self.db.execute(select(Permission))
        return list(result.scalars().all())

    # ============================================================
    # USER ROLE ASSIGNMENT
    # ============================================================

    async def assign_role(
        self,
        user_id: UUID,
        role_id: UUID,
        scope_type: str | None = None,
        scope_id: UUID | None = None,
        valid_until: datetime | None = None,
        granted_by_id: UUID | None = None,
    ) -> UserRole:
        """
        Assign a role to a user.

        Args:
            user_id: User to assign role to
            role_id: Role to assign
            scope_type: Optional scope type (e.g., "entity", "department")
            scope_id: Optional scope ID
            valid_until: Optional expiration date
            granted_by_id: ID of user granting the role

        Returns:
            UserRole assignment
        """
        assignment = UserRole(
            user_id=user_id,
            role_id=role_id,
            scope_type=scope_type,
            scope_id=scope_id,
            valid_until=valid_until,
            granted_by_id=granted_by_id,
        )
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    async def revoke_role(
        self,
        user_id: UUID,
        role_id: UUID,
        scope_type: str | None = None,
        scope_id: UUID | None = None,
    ) -> bool:
        """Revoke a role from a user."""
        query = delete(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
        if scope_type:
            query = query.where(UserRole.scope_type == scope_type)
        if scope_id:
            query = query.where(UserRole.scope_id == scope_id)

        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount > 0

    async def get_user_roles(
        self,
        user_id: UUID,
        include_expired: bool = False,
    ) -> list[UserRole]:
        """Get all role assignments for a user."""
        query = select(UserRole).where(UserRole.user_id == user_id)

        if not include_expired:
            now = datetime.utcnow()
            query = query.where(UserRole.valid_from <= now)
            query = query.where(
                (UserRole.valid_until.is_(None)) | (UserRole.valid_until > now)
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_permissions(self, user_id: UUID) -> set[str]:
        """Get all permissions for a user via their roles."""
        user_roles = await self.get_user_roles(user_id)
        permissions: set[str] = set()

        for user_role in user_roles:
            role = await self.get_role(user_role.role_id)
            if role:
                for perm in role.permissions:
                    permissions.add(perm.permission_string)

        return permissions

    async def has_permission(
        self,
        user_id: UUID,
        permission: str,
    ) -> bool:
        """Check if user has a specific permission."""
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions or "*" in permissions
