"""
Permission checking dependencies.
"""

from uuid import UUID
from typing import Callable
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.permission import PermissionService
from .database import get_db
from .auth import get_current_user


def require_org_permission(
    permission: str,
    org_id_param: str = "org_id",
) -> Callable:
    """
    Dependency factory for checking organization permissions.

    Usage:
    ```python
    @router.get("/{org_id}/settings")
    async def get_settings(
        org_id: UUID,
        user: User = Depends(require_org_permission("org:settings:read")),
    ):
        ...
    ```
    """

    async def check_permission(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        # Get org_id from path parameters
        org_id = request.path_params.get(org_id_param)

        if not org_id:
            # If no org_id in path, might be in body or query
            # For now, just return user
            return current_user

        try:
            org_uuid = UUID(org_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid org_id")

        # Check permission
        perm_service = PermissionService(db)
        has_permission = await perm_service.has_permission(
            user_id=current_user.id,
            org_id=org_uuid,
            permission=permission,
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )

        return current_user

    return check_permission


def require_project_permission(
    permission: str,
    project_id_param: str = "project_id",
) -> Callable:
    """Dependency factory for checking project permissions."""

    async def check_permission(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        project_id = request.path_params.get(project_id_param)

        if not project_id:
            return current_user

        try:
            project_uuid = UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_id")

        perm_service = PermissionService(db)
        has_permission = await perm_service.has_project_permission(
            user_id=current_user.id,
            project_id=project_uuid,
            permission=permission,
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )

        return current_user

    return check_permission
