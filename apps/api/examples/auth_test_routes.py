"""
Authorization Test Routes - Example endpoints demonstrating all auth features.

This file is provided as a REFERENCE for developers. It shows working examples
of all 4 authorization levels.

TO ENABLE THESE ENDPOINTS (for development/testing):
1. Copy this file to src/api/routes/auth_test.py
2. Add to src/api/routes/__init__.py:

   from .auth_test import router as auth_test_router
   router.include_router(auth_test_router, prefix="/auth-test", tags=["auth-test"])

3. Access endpoints at /api/auth-test/*

NOTE: Do NOT include these endpoints in production deployments.
"""

from fastapi import APIRouter
from src.core.auth import (
    CurrentUser,
    AdminUser,
    OptionalUser,
    Authorize,
    require,
    require_admin,
)

router = APIRouter()


# ============================================================
# LEVEL 1: Basic User Dependencies
# ============================================================

@router.get("/public")
async def public_endpoint():
    """No auth required."""
    return {"message": "This is public"}


@router.get("/authenticated")
async def authenticated_endpoint(user: CurrentUser):
    """Requires any authenticated user."""
    return {
        "message": "You are authenticated",
        "user_id": str(user.id),
        "email": user.email,
        "is_admin": user.is_admin,
    }


@router.get("/optional")
async def optional_auth_endpoint(user: OptionalUser):
    """Works with or without auth."""
    if user:
        return {"authenticated": True, "email": user.email}
    return {"authenticated": False}


@router.get("/admin-only")
async def admin_only_endpoint(user: AdminUser):
    """Requires admin user (using AdminUser type)."""
    return {"message": "Welcome, admin!", "email": user.email}


# ============================================================
# LEVEL 2: Permission Decorators
# ============================================================

@router.get("/with-permission")
@require("test:read")
async def with_permission(user: CurrentUser):
    """Requires 'test:read' permission."""
    return {"message": "You have test:read permission"}


@router.post("/with-multiple-permissions")
@require("test:create", "test:publish")
async def with_multiple_permissions(user: CurrentUser):
    """Requires BOTH permissions (AND logic)."""
    return {"message": "You have both permissions"}


@router.delete("/with-any-permission")
@require(any_of=["test:delete", "admin"])
async def with_any_permission(user: CurrentUser):
    """Requires ANY of these permissions (OR logic)."""
    return {"message": "You have at least one required permission"}


@router.get("/admin-decorator")
@require_admin
async def admin_with_decorator(user: CurrentUser):
    """Requires admin (using @require_admin decorator)."""
    return {"message": "Admin access via decorator"}


# ============================================================
# LEVEL 3: Authorization Service
# ============================================================

@router.get("/authz-check")
async def authz_check(auth: Authorize):
    """Demonstrates Authorize service methods."""
    # Check what permissions user has
    permissions = await auth.get_permissions(auth.actor)

    # Check specific permission (returns bool)
    can_read = await auth.can("test:read")
    can_write = await auth.can("test:write")

    return {
        "user_email": auth.actor.email,
        "is_admin": auth.actor.is_admin,
        "permissions": list(permissions),
        "can_test_read": can_read,
        "can_test_write": can_write,
    }


@router.post("/authz-require")
async def authz_require(auth: Authorize):
    """Demonstrates auth.require() - raises 403 if not allowed."""
    # This will raise HTTPException(403) if user doesn't have permission
    await auth.require("test:action")
    return {"message": "Action authorized"}


# ============================================================
# LEVEL 4: Conditions
# ============================================================

@router.post("/with-conditions")
async def with_conditions(auth: Authorize, amount: int = 100):
    """Demonstrates condition checks."""
    # Create a mock resource for testing
    class MockTransaction:
        def __init__(self):
            self.id = "mock-123"
            self.amount = amount
            self.status = "pending"
            self.created_by_id = None  # Not created by current user

    tx = MockTransaction()

    # Check with conditions
    await auth.require(
        "approve",
        tx,
        conditions={
            "status": "pending",      # Resource must have status=pending
            "not_creator": True,      # User must not be the creator
        }
    )

    return {"message": f"Approved transaction for amount {amount}"}


# ============================================================
# SUMMARY ENDPOINT
# ============================================================

@router.get("/summary")
async def auth_summary(user: CurrentUser):
    """Summary of auth capabilities for current user."""
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
        },
        "auth_levels": {
            "level_1": "CurrentUser/AdminUser dependencies - WORKING",
            "level_2": "@require decorator - Check permissions",
            "level_3": "Authorize service - Fine-grained checks",
            "level_4": "Conditions - ABAC-style rules",
        },
        "test_endpoints": [
            "GET /api/auth-test/public - No auth",
            "GET /api/auth-test/authenticated - Any user",
            "GET /api/auth-test/optional - Optional auth",
            "GET /api/auth-test/admin-only - Admin required",
            "GET /api/auth-test/with-permission - Needs test:read",
            "GET /api/auth-test/authz-check - Shows permissions",
        ]
    }
