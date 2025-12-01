"""
Feature Flag Test Routes - Example endpoints demonstrating feature flags.

This file is provided as a REFERENCE for developers.

TO ENABLE THESE ENDPOINTS (for development/testing):
1. Copy this file to src/api/routes/feature_test.py
2. Add to src/api/routes/__init__.py:

   from .feature_test import router as feature_test_router
   router.include_router(feature_test_router, prefix="/feature-test", tags=["feature-test"])

3. Access endpoints at /api/feature-test/*

NOTE: Do NOT include these endpoints in production deployments.
"""

from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter

from src.core.auth import CurrentUser, AdminUser
from src.core.features import (
    Feature,
    UserFeature,
    require_feature,
)

router = APIRouter()


# ============================================================
# LEVEL 1: Simple Check
# ============================================================

@router.get("/simple")
async def simple_check(feature: Feature):
    """Check feature without user context."""
    new_dashboard = await feature.is_enabled("new_dashboard")
    beta_feature = await feature.is_enabled("beta_feature")

    return {
        "new_dashboard": new_dashboard,
        "beta_feature": beta_feature,
    }


# ============================================================
# LEVEL 2: User-Targeted
# ============================================================

@router.get("/user-targeted")
async def user_targeted(feature: UserFeature, user: CurrentUser):
    """Check features with user targeting."""
    # These use the current user automatically
    advanced = await feature.is_enabled("advanced_analytics")
    premium = await feature.is_enabled("premium_reports")

    return {
        "user_email": user.email,
        "advanced_analytics": advanced,
        "premium_reports": premium,
    }


@router.get("/all-flags")
async def all_flags(feature: UserFeature, user: CurrentUser):
    """Get all flags for current user (for frontend)."""
    flags = await feature.get_all()
    return {
        "user_email": user.email,
        "flags": flags,
    }


# ============================================================
# LEVEL 3: Decorator Style
# ============================================================

@router.get("/gated-feature")
@require_feature("gated_feature")
async def gated_feature(feature: UserFeature, user: CurrentUser):
    """This endpoint only works if 'gated_feature' is enabled."""
    return {"message": "You have access to the gated feature!"}


@router.get("/gated-403")
@require_feature("premium_only", status_code=403, detail="Premium subscription required")
async def premium_only(feature: UserFeature, user: CurrentUser):
    """Returns 403 if feature is disabled."""
    return {"message": "Welcome, premium user!"}


# ============================================================
# LEVEL 4: Detailed Evaluation
# ============================================================

@router.get("/evaluate/{key}")
async def evaluate_flag(key: str, feature: UserFeature, user: CurrentUser):
    """Evaluate a flag with detailed result (for debugging)."""
    result = await feature.evaluate(key)

    return {
        "flag_key": result.flag_key,
        "enabled": result.enabled,
        "reason": result.reason,
        "user_id": str(result.user_id) if result.user_id else None,
    }


# ============================================================
# LEVEL 5: Management (Admin Only)
# ============================================================

@router.post("/admin/create")
async def create_flag(
    key: str,
    name: str,
    enabled: bool = False,
    percentage: int = 100,
    feature: Feature = None,
    admin: AdminUser = None,
):
    """Create a new feature flag."""
    flag = await feature.create_flag(
        key=key,
        name=name,
        enabled=enabled,
        percentage=percentage,
    )
    return {
        "created": True,
        "flag": {
            "key": flag.key,
            "name": flag.name,
            "enabled": flag.enabled,
            "percentage": flag.percentage,
        }
    }


@router.get("/admin/list")
async def list_flags(feature: Feature, admin: AdminUser):
    """List all feature flags."""
    flags = await feature.list_flags()
    return {
        "count": len(flags),
        "flags": [
            {
                "key": f.key,
                "name": f.name,
                "enabled": f.enabled,
                "percentage": f.percentage,
                "conditions": f.conditions,
            }
            for f in flags
        ]
    }


@router.patch("/admin/{key}/toggle")
async def toggle_flag(key: str, enabled: bool, feature: Feature, admin: AdminUser):
    """Enable or disable a flag."""
    flag = await feature.update_flag(key, enabled=enabled)
    if not flag:
        return {"error": "Flag not found"}

    return {
        "key": flag.key,
        "enabled": flag.enabled,
    }


@router.patch("/admin/{key}/percentage")
async def set_percentage(key: str, percentage: int, feature: Feature, admin: AdminUser):
    """Set rollout percentage."""
    flag = await feature.update_flag(key, percentage=percentage)
    if not flag:
        return {"error": "Flag not found"}

    return {
        "key": flag.key,
        "percentage": flag.percentage,
    }


@router.delete("/admin/{key}")
async def delete_flag(key: str, feature: Feature, admin: AdminUser):
    """Delete a feature flag."""
    deleted = await feature.delete_flag(key)
    return {"deleted": deleted}


# ============================================================
# GROUP MANAGEMENT
# ============================================================

@router.post("/admin/groups/{group}/add/{user_id}")
async def add_to_group(group: str, user_id: UUID, feature: Feature, admin: AdminUser):
    """Add user to a feature group."""
    added = await feature.add_to_group(user_id, group)
    return {"added": added, "group": group, "user_id": str(user_id)}


@router.delete("/admin/groups/{group}/remove/{user_id}")
async def remove_from_group(group: str, user_id: UUID, feature: Feature, admin: AdminUser):
    """Remove user from a feature group."""
    removed = await feature.remove_from_group(user_id, group)
    return {"removed": removed, "group": group, "user_id": str(user_id)}


@router.get("/my-groups")
async def my_groups(feature: Feature, user: CurrentUser):
    """Get current user's groups."""
    groups = await feature.get_user_groups(user.id)
    return {"user_id": str(user.id), "groups": list(groups)}


# ============================================================
# OVERRIDE MANAGEMENT
# ============================================================

@router.post("/admin/override")
async def set_override(
    user_id: UUID,
    flag_key: str,
    enabled: bool,
    reason: str | None = None,
    expires_days: int | None = None,
    feature: Feature = None,
    admin: AdminUser = None,
):
    """Set an override for a specific user."""
    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    override = await feature.set_override(
        user_id=user_id,
        flag_key=flag_key,
        enabled=enabled,
        reason=reason,
        expires_at=expires_at,
    )
    return {
        "user_id": str(override.user_id),
        "flag_key": override.flag_key,
        "enabled": override.enabled,
        "reason": override.reason,
        "expires_at": override.expires_at.isoformat() if override.expires_at else None,
    }


@router.delete("/admin/override/{user_id}/{flag_key}")
async def remove_override(user_id: UUID, flag_key: str, feature: Feature, admin: AdminUser):
    """Remove an override."""
    removed = await feature.remove_override(user_id, flag_key)
    return {"removed": removed}


# ============================================================
# SUMMARY
# ============================================================

@router.get("/summary")
async def feature_summary(user: CurrentUser):
    """Summary of feature flag capabilities."""
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
        },
        "usage_levels": {
            "level_1": "Feature dependency - simple checks",
            "level_2": "UserFeature dependency - user-targeted",
            "level_3": "@require_feature decorator - gate endpoints",
            "level_4": "Detailed evaluation - debugging",
            "level_5": "Management - create/update/delete flags",
        },
        "targeting_options": [
            "Percentage rollout (0-100%)",
            "Attribute targeting (tier, country, etc.)",
            "Group membership (beta_testers, internal)",
            "Individual overrides (force on/off)",
        ],
        "test_endpoints": [
            "GET /api/feature-test/simple",
            "GET /api/feature-test/user-targeted",
            "GET /api/feature-test/all-flags",
            "GET /api/feature-test/gated-feature",
            "GET /api/feature-test/evaluate/{key}",
            "POST /api/feature-test/admin/create",
            "GET /api/feature-test/admin/list",
        ]
    }
