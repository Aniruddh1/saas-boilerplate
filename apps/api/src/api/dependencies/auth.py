"""
Authentication dependencies.
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt

from src.core.config import settings
from src.models.user import User
from src.services.auth import AuthService
from src.services.user import UserService
from src.services.api_key import APIKeyService
from .database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    api_key: str | None = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user.
    Supports both JWT token and API key authentication.
    """
    # Try API key first
    if api_key:
        api_key_service = APIKeyService(db)
        user = await api_key_service.authenticate(api_key)
        if user:
            return user

    # Try JWT token
    if token:
        try:
            payload = jwt.decode(
                token,
                settings.auth.secret_key,
                algorithms=[settings.auth.algorithm],
            )
            user_id = payload.get("sub")
            if user_id:
                user_service = UserService(db)
                user = await user_service.get_by_id(user_id)
                if user:
                    return user
        except JWTError:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    api_key: str | None = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user if authenticated, None otherwise."""
    if not token and not api_key:
        return None

    try:
        return await get_current_user(token, api_key, db)
    except HTTPException:
        return None


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require admin user."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# Type aliases for cleaner signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
AdminUser = Annotated[User, Depends(require_admin)]
