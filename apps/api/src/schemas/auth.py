"""
Authentication schemas.
"""

from pydantic import BaseModel, EmailStr, Field

from .user import UserResponse


class TokenResponse(BaseModel):
    """Token pair response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=255)


class RegisterResponse(BaseModel):
    """Registration response with user and tokens."""
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # User ID
    exp: int  # Expiration timestamp
    type: str  # "access" or "refresh"
