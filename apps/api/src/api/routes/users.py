"""
User management routes.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.schemas.user import UserResponse, UserUpdate, UserListResponse
from src.services.user import UserService
from src.api.dependencies.auth import get_current_user, require_admin
from src.api.dependencies.services import get_user_service
from src.models.user import User

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    data: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
):
    """Update current user profile."""
    user = await user_service.update(current_user.id, data)
    return UserResponse.model_validate(user)


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = None,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require_admin),
):
    """List all users (admin only)."""
    users, total = await user_service.list_users(
        page=page,
        per_page=per_page,
        search=search,
    )
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
):
    """Get user by ID."""
    # Users can only view themselves unless admin
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
):
    """Update user."""
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    user = await user_service.update(user_id, data)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require_admin),
):
    """Delete user (admin only)."""
    deleted = await user_service.delete(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
