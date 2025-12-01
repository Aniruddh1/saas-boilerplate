"""Audit log API routes."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_db
from src.models.user import User
from src.schemas.audit_log import AuditLogFilter, AuditLogResponse
from src.services.audit import AuditLogService

router = APIRouter()


async def get_audit_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AuditLogService:
    return AuditLogService(db)


@router.get("", response_model=list[AuditLogResponse])
async def list_audit_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuditLogService, Depends(get_audit_service)],
    actor_id: Optional[UUID] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List audit logs.

    Supports filtering by actor, resource type, resource ID, and action.
    Users see only their own actions by default.
    """
    filters = AuditLogFilter(
        actor_id=actor_id or current_user.id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
    )

    logs = await service.list(
        filters=filters,
        limit=limit,
        offset=offset,
    )
    return logs


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuditLogService, Depends(get_audit_service)],
):
    """Get a specific audit log entry."""
    log = await service.get(log_id)
    if not log:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )
    # Users can only see their own logs
    if log.actor_id != current_user.id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return log
