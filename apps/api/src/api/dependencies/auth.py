"""
Authentication dependencies.

This module re-exports from the new core auth system for backward compatibility.
For new code, import directly from src.core.auth.

Usage:
    from src.api.dependencies.auth import CurrentUser, AdminUser, Authorize

    # Or from the new location:
    from src.core.auth import CurrentUser, AdminUser, Authorize
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import AuthService
from .database import get_db

# Re-export everything from the new core auth module
from src.core.auth import (
    # Dependencies
    CurrentUser,
    OptionalUser,
    AdminUser,
    Authorize,
    get_current_user,
    get_current_user_optional,
    require_admin_user as require_admin,
    get_authorization_service,
    # Decorators
    require,
    require_admin as require_admin_decorator,
    # Interfaces (for type hints)
    PolicyEngine,
    ScopeProvider,
    PolicyDecision,
    AuthorizationService,
)


# Keep the AuthService dependency for authentication (login/register)
async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Get auth service instance (for login/register)."""
    return AuthService(db)


__all__ = [
    # User dependencies
    "CurrentUser",
    "OptionalUser",
    "AdminUser",
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    # Authorization
    "Authorize",
    "get_authorization_service",
    "require",
    "require_admin_decorator",
    # Interfaces
    "PolicyEngine",
    "ScopeProvider",
    "PolicyDecision",
    "AuthorizationService",
    # Auth service (for login/register)
    "get_auth_service",
]
