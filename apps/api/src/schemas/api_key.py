"""
API Key schemas.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from src.models.api_key import APIKeyType


class APIKeyCreate(BaseModel):
    """API key creation schema."""
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    key_type: APIKeyType = APIKeyType.SERVER
    org_id: UUID | None = None
    project_id: UUID | None = None
    actions: list[str] = ["*"]
    resources: list[str] = ["*"]
    rate_limit: int | None = None
    expires_at: datetime | None = None


class APIKeyResponse(BaseModel):
    """API key response schema (without full key)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key_prefix: str
    name: str
    description: str | None = None
    key_type: APIKeyType
    org_id: UUID | None = None
    project_id: UUID | None = None
    actions: list[str]
    resources: list[str]
    rate_limit: int | None = None
    expires_at: datetime | None = None
    created_at: datetime
    last_used_at: datetime | None = None
    use_count: int


class APIKeyCreatedResponse(BaseModel):
    """Response when API key is created (includes full key once)."""
    key: str  # Full key, only shown once
    api_key: APIKeyResponse


class APIKeyListResponse(BaseModel):
    """API key list response."""
    api_keys: list[APIKeyResponse]
