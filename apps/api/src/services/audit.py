"""Audit log service for tracking changes."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLog
from src.models.user import User
from src.schemas.audit_log import AuditAction, AuditLogFilter

logger = structlog.get_logger()


def compute_changes(old: dict, new: dict) -> dict[str, dict[str, Any]]:
    """
    Compute the differences between two dictionaries.

    Returns a dict of changed fields with old and new values.
    """
    changes = {}
    all_keys = set(old.keys()) | set(new.keys())

    for key in all_keys:
        old_value = old.get(key)
        new_value = new.get(key)

        if old_value != new_value:
            changes[key] = {"old": old_value, "new": new_value}

    return changes


class AuditLogService:
    """Service for managing audit logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        actor: Optional[User] = None,
        actor_id: Optional[UUID] = None,
        actor_email: Optional[str] = None,
        actor_ip: Optional[str] = None,
        actor_user_agent: Optional[str] = None,
        org_id: Optional[UUID] = None,
        changes: Optional[dict] = None,
        extra_data: Optional[dict] = None,
        summary: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: The action performed (use AuditAction constants)
            resource_type: Type of resource affected (e.g., "user", "project")
            resource_id: ID of the affected resource
            actor: User who performed the action
            actor_id: ID of the actor (if actor not provided)
            actor_email: Email of the actor (denormalized)
            actor_ip: IP address of the actor
            actor_user_agent: User agent of the actor
            org_id: Organization context
            changes: Dict of field changes {"field": {"old": x, "new": y}}
            extra_data: Additional context
            summary: Human-readable summary
            request_id: Request ID for correlation
        """
        # Extract actor info
        if actor:
            actor_id = actor.id
            actor_email = actor.email

        entry = AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            org_id=org_id,
            resource_type=resource_type,
            resource_id=str(resource_id),
            action=action,
            changes=changes,
            extra_data=extra_data,
            summary=summary or self._generate_summary(action, resource_type, actor_email),
            request_id=request_id,
        )

        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)

        logger.info(
            "Audit log created",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=str(actor_id) if actor_id else None,
        )

        return entry

    def _generate_summary(
        self,
        action: str,
        resource_type: str,
        actor_email: Optional[str]
    ) -> str:
        """Generate a human-readable summary."""
        actor = actor_email or "System"
        action_past = {
            AuditAction.CREATE: "created",
            AuditAction.UPDATE: "updated",
            AuditAction.DELETE: "deleted",
            AuditAction.LOGIN: "logged in",
            AuditAction.LOGOUT: "logged out",
            AuditAction.LOGIN_FAILED: "failed to log in",
            AuditAction.PASSWORD_CHANGED: "changed password for",
            AuditAction.PASSWORD_RESET: "reset password for",
            AuditAction.INVITE_SENT: "sent invite for",
            AuditAction.INVITE_ACCEPTED: "accepted invite for",
            AuditAction.ROLE_CHANGED: "changed role for",
            AuditAction.API_KEY_CREATED: "created API key for",
            AuditAction.API_KEY_REVOKED: "revoked API key for",
        }.get(action, action)

        if action in [AuditAction.LOGIN, AuditAction.LOGOUT, AuditAction.LOGIN_FAILED]:
            return f"{actor} {action_past}"

        return f"{actor} {action_past} {resource_type}"

    async def get(self, log_id: UUID) -> Optional[AuditLog]:
        """Get an audit log by ID."""
        return await self.db.get(AuditLog, log_id)

    async def list(
        self,
        *,
        org_id: Optional[UUID] = None,
        filters: Optional[AuditLogFilter] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs with optional filtering."""
        query = select(AuditLog)

        if org_id:
            query = query.where(AuditLog.org_id == org_id)

        if filters:
            if filters.actor_id:
                query = query.where(AuditLog.actor_id == filters.actor_id)
            if filters.resource_type:
                query = query.where(AuditLog.resource_type == filters.resource_type)
            if filters.resource_id:
                query = query.where(AuditLog.resource_id == filters.resource_id)
            if filters.action:
                query = query.where(AuditLog.action == filters.action)
            if filters.start_date:
                query = query.where(AuditLog.created_at >= filters.start_date)
            if filters.end_date:
                query = query.where(AuditLog.created_at <= filters.end_date)

        query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def log_create(
        self,
        *,
        resource_type: str,
        resource_id: str,
        resource_data: dict,
        actor: Optional[User] = None,
        org_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> AuditLog:
        """Convenience method for logging create actions."""
        return await self.log(
            action=AuditAction.CREATE,
            resource_type=resource_type,
            resource_id=resource_id,
            actor=actor,
            org_id=org_id,
            changes={"created": resource_data},
            request_id=request_id,
            actor_ip=actor_ip,
        )

    async def log_update(
        self,
        *,
        resource_type: str,
        resource_id: str,
        old_data: dict,
        new_data: dict,
        actor: Optional[User] = None,
        org_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> Optional[AuditLog]:
        """Convenience method for logging update actions."""
        changes = compute_changes(old_data, new_data)

        if not changes:
            return None  # No actual changes

        return await self.log(
            action=AuditAction.UPDATE,
            resource_type=resource_type,
            resource_id=resource_id,
            actor=actor,
            org_id=org_id,
            changes=changes,
            request_id=request_id,
            actor_ip=actor_ip,
        )

    async def log_delete(
        self,
        *,
        resource_type: str,
        resource_id: str,
        resource_data: Optional[dict] = None,
        actor: Optional[User] = None,
        org_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> AuditLog:
        """Convenience method for logging delete actions."""
        return await self.log(
            action=AuditAction.DELETE,
            resource_type=resource_type,
            resource_id=resource_id,
            actor=actor,
            org_id=org_id,
            changes={"deleted": resource_data} if resource_data else None,
            request_id=request_id,
            actor_ip=actor_ip,
        )
