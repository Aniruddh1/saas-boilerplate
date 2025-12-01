"""
Feature flags API routes.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.auth import CurrentUser, AdminUser
from src.core.features import Feature, UserFeature

router = APIRouter()


# ============================================================
# SCHEMAS
# ============================================================

class FeatureFlagCreate(BaseModel):
    """Create a new feature flag."""
    key: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    enabled: bool = False
    percentage: int = Field(default=100, ge=0, le=100)
    conditions: dict[str, Any] | None = None


class FeatureFlagUpdate(BaseModel):
    """Update a feature flag."""
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    percentage: int | None = Field(default=None, ge=0, le=100)
    conditions: dict[str, Any] | None = None


class FeatureFlagResponse(BaseModel):
    """Feature flag response."""
    id: str
    key: str
    name: str
    description: str | None
    enabled: bool
    percentage: int
    conditions: dict[str, Any]
    created_at: str
    updated_at: str


# ============================================================
# USER ENDPOINTS
# ============================================================

@router.get("/me")
async def get_my_flags(
    feature: UserFeature,
    user: CurrentUser,
) -> dict[str, bool]:
    """
    Get all feature flags for the current user.

    Returns a dictionary of flag_key -> enabled status.
    Useful for frontend to fetch all flags at once.
    """
    return await feature.get_all()


@router.get("/check/{key}")
async def check_flag(
    key: str,
    feature: UserFeature,
    user: CurrentUser,
) -> dict[str, Any]:
    """
    Check if a specific feature flag is enabled for the current user.
    """
    result = await feature.evaluate(key)
    return {
        "key": result.flag_key,
        "enabled": result.enabled,
        "reason": result.reason,
    }


# ============================================================
# ADMIN ENDPOINTS
# ============================================================

@router.get("")
async def list_flags(
    feature: Feature,
    admin: AdminUser,
) -> list[dict[str, Any]]:
    """
    List all feature flags.
    Admin only.
    """
    flags = await feature.list_flags()
    return [
        {
            "id": str(f.id) if hasattr(f, 'id') else f.key,
            "key": f.key,
            "name": f.name,
            "description": getattr(f, 'description', None),
            "enabled": f.enabled,
            "percentage": f.percentage,
            "conditions": f.conditions,
            "created_at": getattr(f, 'created_at', None),
            "updated_at": getattr(f, 'updated_at', None),
        }
        for f in flags
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_flag(
    data: FeatureFlagCreate,
    feature: Feature,
    admin: AdminUser,
) -> dict[str, Any]:
    """
    Create a new feature flag.
    Admin only.
    """
    try:
        flag = await feature.create_flag(
            key=data.key,
            name=data.name,
            description=data.description,
            enabled=data.enabled,
            percentage=data.percentage,
            conditions=data.conditions or {},
        )
        return {
            "id": str(flag.id) if hasattr(flag, 'id') else flag.key,
            "key": flag.key,
            "name": flag.name,
            "description": getattr(flag, 'description', None),
            "enabled": flag.enabled,
            "percentage": flag.percentage,
            "conditions": flag.conditions,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{key}")
async def get_flag(
    key: str,
    feature: Feature,
    admin: AdminUser,
) -> dict[str, Any]:
    """
    Get a specific feature flag by key.
    Admin only.
    """
    flag = await feature.get_flag(key)
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{key}' not found",
        )
    return {
        "id": str(flag.id) if hasattr(flag, 'id') else flag.key,
        "key": flag.key,
        "name": flag.name,
        "description": getattr(flag, 'description', None),
        "enabled": flag.enabled,
        "percentage": flag.percentage,
        "conditions": flag.conditions,
    }


@router.patch("/{key}")
async def update_flag(
    key: str,
    data: FeatureFlagUpdate,
    feature: Feature,
    admin: AdminUser,
) -> dict[str, Any]:
    """
    Update a feature flag.
    Admin only.
    """
    # Build update dict with only provided fields
    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.description is not None:
        updates["description"] = data.description
    if data.enabled is not None:
        updates["enabled"] = data.enabled
    if data.percentage is not None:
        updates["percentage"] = data.percentage
    if data.conditions is not None:
        updates["conditions"] = data.conditions

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    flag = await feature.update_flag(key, **updates)
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{key}' not found",
        )

    return {
        "id": str(flag.id) if hasattr(flag, 'id') else flag.key,
        "key": flag.key,
        "name": flag.name,
        "description": getattr(flag, 'description', None),
        "enabled": flag.enabled,
        "percentage": flag.percentage,
        "conditions": flag.conditions,
    }


@router.delete("/{key}")
async def delete_flag(
    key: str,
    feature: Feature,
    admin: AdminUser,
) -> dict[str, bool]:
    """
    Delete a feature flag.
    Admin only.
    """
    deleted = await feature.delete_flag(key)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{key}' not found",
        )
    return {"deleted": True}
