"""Audit log schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    id: UUID
    actor_id: Optional[UUID]
    actor_email: Optional[str]
    actor_ip: Optional[str]
    org_id: Optional[UUID]
    resource_type: str
    resource_id: str
    action: str
    changes: Optional[dict]
    extra_data: Optional[dict]
    summary: Optional[str]
    request_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs."""

    actor_id: Optional[UUID] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# Standard audit actions
class AuditAction:
    """Standard audit action constants."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    INVITE_SENT = "invite_sent"
    INVITE_ACCEPTED = "invite_accepted"
    ROLE_CHANGED = "role_changed"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    EXPORT = "export"
    IMPORT = "import"
