"""
FastAPI dependencies for authorization.

Usage:
    from src.core.auth import CurrentUser, AdminUser, Authorize

    @router.get("/protected")
    async def handler(user: CurrentUser):
        ...

    @router.get("/admin")
    async def handler(user: AdminUser):
        ...

    @router.post("/approve/{id}")
    async def handler(id: UUID, auth: Authorize):
        await auth.require("approve", resource)
"""

from typing import Annotated, Any
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.user import User
from src.services.user import UserService
from src.api.dependencies.database import get_db

from .service import AuthorizationService
from .interfaces import PolicyEngine, ScopeProvider
from .registry import AuthRegistry

# Import to register default implementations
from . import policy  # noqa: F401
from . import scope  # noqa: F401
from . import conditions  # noqa: F401


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ============================================================
# COMPONENT FACTORIES
# ============================================================

@lru_cache
def get_policy_engine() -> PolicyEngine:
    """
    Get configured policy engine.

    Reads from AUTH_POLICY_ENGINE environment variable.
    Default: "simple" (just is_admin check)
    """
    engine_name = settings.auth.policy_engine

    return AuthRegistry.get_policy_engine(engine_name)


@lru_cache
def get_scope_provider() -> ScopeProvider:
    """
    Get configured scope provider.

    Reads from AUTH_SCOPE_PROVIDER environment variable.
    Default: "none" (no data filtering)
    """
    provider_name = settings.auth.scope_provider

    # Get provider-specific config
    provider_config = {
        "multi_tenant": settings.auth.multi_tenant,
        "tenant_field": settings.auth.tenant_field,
    }

    return AuthRegistry.get_scope_provider(provider_name, **provider_config)


# ============================================================
# USER DEPENDENCIES
# ============================================================

async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Raises:
        HTTPException 401: If not authenticated
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            settings.auth.secret_key,
            algorithms=[settings.auth.algorithm],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        user_service = UserService(db)
        user = await user_service.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive",
            )

        return user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Get current user if authenticated, None otherwise.
    Does not raise if not authenticated.
    """
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


async def require_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require current user to be admin.

    Raises:
        HTTPException 403: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ============================================================
# AUTHORIZATION SERVICE DEPENDENCY
# ============================================================

async def get_authorization_service(
    current_user: User = Depends(get_current_user),
) -> AuthorizationService:
    """
    Get authorization service for current user.

    Usage:
        async def handler(auth: Authorize):
            await auth.require("action", resource)
    """
    return AuthorizationService(
        actor=current_user,
        policy_engine=get_policy_engine(),
        scope_provider=get_scope_provider(),
    )


# ============================================================
# TYPE ALIASES FOR CLEAN SIGNATURES
# ============================================================

# Authenticated user (required)
CurrentUser = Annotated[User, Depends(get_current_user)]

# Authenticated user (optional)
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]

# Admin user (required)
AdminUser = Annotated[User, Depends(require_admin_user)]

# Authorization service
Authorize = Annotated[AuthorizationService, Depends(get_authorization_service)]
