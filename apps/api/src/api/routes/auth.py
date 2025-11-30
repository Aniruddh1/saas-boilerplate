"""
Authentication routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.schemas.auth import (
    TokenResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
)
from src.schemas.user import UserResponse
from src.services.auth import AuthService
from src.api.dependencies.auth import get_current_user, get_auth_service
from src.models.user import User

router = APIRouter()


@router.post("/register", response_model=RegisterResponse)
async def register(
    data: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user."""
    user, tokens = await auth_service.register(
        email=data.email,
        password=data.password,
        name=data.name,
    )
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type="bearer",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Login with email and password."""
    tokens = await auth_service.login(
        email=form_data.username,
        password=form_data.password,
    )
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh access token."""
    tokens = await auth_service.refresh_tokens(data.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type="bearer",
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Logout current user (invalidate tokens)."""
    await auth_service.logout(current_user.id)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse.model_validate(current_user)
