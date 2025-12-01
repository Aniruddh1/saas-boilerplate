"""
Audit log API routes.

Demonstrates enterprise pagination patterns:
- Offset pagination (GET /audit-logs) - for admin tables
- Cursor pagination (GET /audit-logs/stream) - for infinite scroll
- Export (GET /audit-logs/export) - for bulk data
- Count (GET /audit-logs/count) - for UI badges
"""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user, require_admin
from src.api.dependencies.database import get_db
from src.models.audit_log import AuditLog
from src.models.user import User
from src.schemas.audit_log import AuditLogFilter, AuditLogResponse
from src.services.audit import AuditLogService
from src.utils.pagination import (
    Paginator,
    ExportFormat,
    stream_query,
    create_csv_streaming_response,
    create_jsonl_streaming_response,
    get_offset_params,
    get_cursor_params,
    OffsetParams,
    CursorParams,
)

router = APIRouter()


async def get_audit_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AuditLogService:
    return AuditLogService(db)


def serialize_audit_log(log: AuditLog) -> dict[str, Any]:
    """Serialize audit log for export."""
    return {
        "id": str(log.id),
        "actor_id": str(log.actor_id) if log.actor_id else None,
        "actor_email": log.actor_email,
        "actor_ip": log.actor_ip,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "action": log.action,
        "summary": log.summary,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def build_query(
    filters: AuditLogFilter,
    current_user: User,
    is_admin: bool = False,
):
    """Build base query with filters applied."""
    query = select(AuditLog)

    # Non-admins can only see their own logs
    if not is_admin:
        query = query.where(AuditLog.actor_id == current_user.id)
    elif filters.actor_id:
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

    return query


# ============================================================
# OFFSET PAGINATION (Traditional - for admin tables)
# ============================================================

@router.get("")
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    pagination: Annotated[OffsetParams, Depends(get_offset_params)],
    actor_id: UUID | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    action: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> dict[str, Any]:
    """
    List audit logs with offset pagination.

    Best for admin tables with page numbers.

    Returns:
        {
            "items": [...],
            "total": 150,
            "page": 1,
            "per_page": 20,
            "pages": 8,
            "has_next": true,
            "has_prev": false
        }
    """
    filters = AuditLogFilter(
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
    )

    query = build_query(filters, current_user, current_user.is_admin)
    query = query.order_by(AuditLog.created_at.desc())

    paginator = Paginator(db)
    page = await paginator.paginate_offset(
        query,
        page=pagination.page,
        per_page=pagination.per_page,
    )

    return {
        "items": [AuditLogResponse.model_validate(log) for log in page.items],
        "total": page.total,
        "page": page.page,
        "per_page": page.per_page,
        "pages": page.pages,
        "has_next": page.has_next,
        "has_prev": page.has_prev,
    }


# ============================================================
# CURSOR PAGINATION (For infinite scroll / real-time)
# ============================================================

@router.get("/stream")
async def stream_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    pagination: Annotated[CursorParams, Depends(get_cursor_params)],
    resource_type: str | None = Query(None),
    action: str | None = Query(None),
) -> dict[str, Any]:
    """
    List audit logs with cursor pagination.

    Best for infinite scroll and real-time feeds.
    No total count (more efficient for large datasets).

    Returns:
        {
            "items": [...],
            "next_cursor": "abc123",
            "prev_cursor": "xyz789",
            "has_next": true,
            "has_prev": true,
            "limit": 20
        }
    """
    filters = AuditLogFilter(
        resource_type=resource_type,
        action=action,
    )

    query = build_query(filters, current_user, current_user.is_admin)

    paginator = Paginator(db)
    page = await paginator.paginate_cursor(
        query,
        cursor=pagination.cursor,
        limit=pagination.limit,
        order_column=AuditLog.created_at,
        id_column=AuditLog.id,
        descending=True,
    )

    return {
        "items": [AuditLogResponse.model_validate(log) for log in page.items],
        "next_cursor": page.next_cursor,
        "prev_cursor": page.prev_cursor,
        "has_next": page.has_next,
        "has_prev": page.has_prev,
        "limit": page.limit,
    }


# ============================================================
# COUNT ONLY (For UI badges)
# ============================================================

@router.get("/count")
async def count_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    resource_type: str | None = Query(None),
    action: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> dict[str, int]:
    """
    Get count of audit logs matching filters.

    Useful for UI badges and dashboard stats.
    """
    filters = AuditLogFilter(
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
    )

    query = build_query(filters, current_user, current_user.is_admin)

    paginator = Paginator(db)
    count = await paginator.count(query)

    return {"count": count}


# ============================================================
# EXPORT (Streaming bulk data)
# ============================================================

@router.get("/export")
async def export_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],  # Admin only
    format: ExportFormat = Query(ExportFormat.CSV),
    resource_type: str | None = Query(None),
    action: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> StreamingResponse:
    """
    Export audit logs as CSV or JSONL.

    Admin only. Streams data for memory efficiency.

    Query params:
        format: "csv" or "jsonl"
        resource_type: Filter by resource type
        action: Filter by action
        start_date: Filter from date
        end_date: Filter to date
    """
    filters = AuditLogFilter(
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
    )

    # Admin can see all logs
    query = select(AuditLog)

    if filters.resource_type:
        query = query.where(AuditLog.resource_type == filters.resource_type)
    if filters.action:
        query = query.where(AuditLog.action == filters.action)
    if filters.start_date:
        query = query.where(AuditLog.created_at >= filters.start_date)
    if filters.end_date:
        query = query.where(AuditLog.created_at <= filters.end_date)

    query = query.order_by(AuditLog.created_at.desc())

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == ExportFormat.CSV:
        return create_csv_streaming_response(
            stream_query(db, query),
            serialize_audit_log,
            filename=f"audit_logs_{timestamp}.csv",
        )
    else:
        return create_jsonl_streaming_response(
            stream_query(db, query),
            serialize_audit_log,
            filename=f"audit_logs_{timestamp}.jsonl",
        )


# ============================================================
# SINGLE LOG (Detail view)
# ============================================================

@router.get("/{log_id}")
async def get_audit_log(
    log_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuditLogService, Depends(get_audit_service)],
) -> AuditLogResponse:
    """Get a specific audit log entry."""
    log = await service.get(log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )
    # Users can only see their own logs unless admin
    if log.actor_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return AuditLogResponse.model_validate(log)
