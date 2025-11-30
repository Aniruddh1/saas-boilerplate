"""
User schemas.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserResponse(BaseModel):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str
    is_active: bool
    is_verified: bool
    avatar_url: str | None = None
    timezone: str
    created_at: datetime
    last_login_at: datetime | None = None


class UserUpdate(BaseModel):
    """User update schema."""
    name: str | None = Field(None, min_length=1, max_length=255)
    avatar_url: str | None = Field(None, max_length=500)
    timezone: str | None = Field(None, max_length=50)


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: list[UserResponse]
    total: int
    page: int
    per_page: int
