"""
Organization schemas.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from src.models.org import OrgRole


class OrgCreate(BaseModel):
    """Organization creation schema."""
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(None, max_length=1000)


class OrgUpdate(BaseModel):
    """Organization update schema."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    billing_email: str | None = None
    settings: dict | None = None


class OrgResponse(BaseModel):
    """Organization response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None = None
    plan: str
    created_at: datetime


class OrgListResponse(BaseModel):
    """Paginated organization list response."""
    orgs: list[OrgResponse]
    total: int
    page: int
    per_page: int


class MemberUserInfo(BaseModel):
    """User info embedded in member response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None


class OrgMemberResponse(BaseModel):
    """Organization member response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    role: OrgRole
    user: MemberUserInfo
    created_at: datetime


class AddMemberRequest(BaseModel):
    """Add member request."""
    user_id: UUID
    role: OrgRole = OrgRole.MEMBER


class UpdateMemberRequest(BaseModel):
    """Update member role request."""
    role: OrgRole
