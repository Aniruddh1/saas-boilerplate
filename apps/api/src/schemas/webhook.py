"""Webhook schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class WebhookCreate(BaseModel):
    """Schema for creating a webhook."""

    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    secret: Optional[str] = Field(None, max_length=255)
    events: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    headers: Optional[dict[str, str]] = None
    is_active: bool = True
    max_failures: int = Field(default=5, ge=1, le=100)


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[HttpUrl] = None
    secret: Optional[str] = Field(None, max_length=255)
    events: Optional[list[str]] = None
    description: Optional[str] = None
    headers: Optional[dict[str, str]] = None
    is_active: Optional[bool] = None
    max_failures: Optional[int] = Field(None, ge=1, le=100)


class WebhookResponse(BaseModel):
    """Schema for webhook response."""

    id: UUID
    org_id: UUID
    name: str
    url: str
    events: list[str]
    is_active: bool
    description: Optional[str]
    headers: Optional[dict[str, str]]
    max_failures: int
    failure_count: int
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookLogResponse(BaseModel):
    """Schema for webhook log response."""

    id: UUID
    webhook_id: UUID
    event_type: str
    payload: dict
    response_status: Optional[int]
    response_time_ms: Optional[int]
    attempt: int
    success: bool
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookTestRequest(BaseModel):
    """Schema for testing a webhook."""

    event_type: str = "test.ping"
    payload: Optional[dict] = None


class WebhookTestResponse(BaseModel):
    """Schema for webhook test response."""

    success: bool
    status_code: Optional[int]
    response_time_ms: int
    error: Optional[str]


# Event types that can trigger webhooks
WEBHOOK_EVENTS = [
    # User events
    "user.created",
    "user.updated",
    "user.deleted",

    # Org events
    "org.created",
    "org.updated",
    "org.deleted",
    "org.member.added",
    "org.member.removed",

    # Project events
    "project.created",
    "project.updated",
    "project.deleted",

    # API key events
    "api_key.created",
    "api_key.revoked",

    # Test event
    "test.ping",
]
