"""
Project schemas.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ProjectCreate(BaseModel):
    """Project creation schema."""
    org_id: UUID
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(None, max_length=1000)


class ProjectUpdate(BaseModel):
    """Project update schema."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    settings: dict | None = None


class ProjectResponse(BaseModel):
    """Project response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    name: str
    slug: str
    description: str | None = None
    created_at: datetime


class ProjectListResponse(BaseModel):
    """Paginated project list response."""
    projects: list[ProjectResponse]
    total: int
    page: int
    per_page: int
