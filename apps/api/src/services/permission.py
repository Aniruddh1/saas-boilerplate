"""
Permission service.
"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.org import OrgMember, OrgRole, ROLE_LEVELS
from src.models.project import Project


# Permission definitions
PERMISSIONS = {
    # Organization permissions
    "org:read": OrgRole.VIEWER,
    "org:update": OrgRole.ADMIN,
    "org:delete": OrgRole.OWNER,
    "org:members:read": OrgRole.MEMBER,
    "org:members:manage": OrgRole.ADMIN,
    "org:settings:read": OrgRole.ADMIN,
    "org:settings:update": OrgRole.OWNER,
    "org:billing:read": OrgRole.ADMIN,
    "org:billing:update": OrgRole.OWNER,

    # Project permissions
    "project:create": OrgRole.MEMBER,
    "project:read": OrgRole.VIEWER,
    "project:update": OrgRole.MEMBER,
    "project:delete": OrgRole.ADMIN,

    # API Key permissions
    "api_key:create": OrgRole.MEMBER,
    "api_key:read": OrgRole.MEMBER,
    "api_key:update": OrgRole.MEMBER,
    "api_key:delete": OrgRole.ADMIN,
}


class PermissionService:
    """Permission checking service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_role(
        self,
        user_id: UUID,
        org_id: UUID,
    ) -> OrgRole | None:
        """Get user's role in organization."""
        stmt = select(OrgMember).where(
            OrgMember.user_id == user_id,
            OrgMember.org_id == org_id,
        )
        result = await self.db.execute(stmt)
        member = result.scalar_one_or_none()
        return member.role if member else None

    async def has_permission(
        self,
        user_id: UUID,
        org_id: UUID,
        permission: str,
    ) -> bool:
        """Check if user has permission in organization."""
        user_role = await self.get_user_role(user_id, org_id)
        if not user_role:
            return False

        required_role = PERMISSIONS.get(permission)
        if not required_role:
            return False

        user_level = ROLE_LEVELS.get(user_role, 0)
        required_level = ROLE_LEVELS.get(required_role, 100)

        return user_level >= required_level

    async def has_project_permission(
        self,
        user_id: UUID,
        project_id: UUID,
        permission: str,
    ) -> bool:
        """Check if user has permission for project."""
        # Get project's org
        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return False

        return await self.has_permission(user_id, project.org_id, permission)

    async def check_permission(
        self,
        user_id: UUID,
        org_id: UUID,
        permission: str,
    ) -> None:
        """Check permission and raise if denied."""
        if not await self.has_permission(user_id, org_id, permission):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
