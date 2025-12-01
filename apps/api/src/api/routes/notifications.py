"""
Notification API routes.

Demonstrates enterprise notification patterns:
- List notifications (GET /notifications) - offset pagination
- Unread count (GET /notifications/unread-count) - for badges
- Mark as read (POST /notifications/{id}/read) - single notification
- Mark all as read (POST /notifications/read-all) - bulk operation
- Delete (DELETE /notifications/{id}) - single notification
- Broadcast (POST /notifications/broadcast) - admin only
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.api.dependencies.auth import get_current_user, require_admin
from src.api.dependencies.database import get_db
from src.models.user import User
from src.utils.pagination import get_offset_params, OffsetParams, OffsetPage
from src.utils.notifications import (
    NotificationResponse,
    NotificationCreate,
    BroadcastRequest,
    BroadcastResult,
    get_database_channel,
    get_notifier,
    create_notification,
    Notifier,
)
from src.implementations.notifications.database import DatabaseNotificationChannel
from src.core.interfaces.notifications import NotificationType, NotificationCategory

router = APIRouter()


# ============================================================
# LIST & COUNT (User's own notifications)
# ============================================================

@router.get("")
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    channel: Annotated[DatabaseNotificationChannel, Depends(get_database_channel)],
    pagination: Annotated[OffsetParams, Depends(get_offset_params)],
    read: Optional[bool] = Query(None, description="Filter by read status"),
) -> OffsetPage[NotificationResponse]:
    """
    List user's notifications with offset pagination.

    Query params:
        page: Page number (1-indexed)
        per_page: Items per page (1-100)
        read: Filter by read status (true/false/null for all)

    Returns paginated notifications, newest first.
    """
    # Get notifications
    notifications = await channel.list_for_user(
        user_id=current_user.id,
        read=read,
        limit=pagination.per_page,
        offset=(pagination.page - 1) * pagination.per_page,
    )

    # Get accurate total count for pagination
    total = await channel.count_total(current_user.id, read=read)

    # Convert to response models
    items = [
        NotificationResponse(
            id=str(n.id),
            type=n.type,
            category=n.category,
            title=n.title,
            message=n.message,
            action_url=n.action_url,
            action_label=n.action_label,
            data=n.data or {},
            read_at=n.read_at.isoformat() if n.read_at else None,
            created_at=n.created_at.isoformat(),
        )
        for n in notifications
    ]

    return OffsetPage.create(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    channel: Annotated[DatabaseNotificationChannel, Depends(get_database_channel)],
) -> dict[str, int]:
    """
    Get count of unread notifications.

    Best for: Badge displays, notification indicators.
    """
    count = await channel.count_unread(current_user.id)
    return {"count": count}


# ============================================================
# SINGLE NOTIFICATION OPERATIONS
# ============================================================

@router.get("/{notification_id}")
async def get_notification(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    channel: Annotated[DatabaseNotificationChannel, Depends(get_database_channel)],
) -> NotificationResponse:
    """Get a single notification by ID."""
    notification = await channel.get(str(notification_id))

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # Check ownership
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return NotificationResponse(
        id=str(notification.id),
        type=notification.type,
        category=notification.category,
        title=notification.title,
        message=notification.message,
        action_url=notification.action_url,
        action_label=notification.action_label,
        data=notification.data or {},
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        created_at=notification.created_at.isoformat(),
    )


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    channel: Annotated[DatabaseNotificationChannel, Depends(get_database_channel)],
) -> dict[str, bool]:
    """Mark a single notification as read."""
    notification = await channel.get(str(notification_id))

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    success = await channel.mark_read(str(notification_id))
    return {"success": success}


@router.post("/read-all")
async def mark_all_as_read(
    current_user: Annotated[User, Depends(get_current_user)],
    channel: Annotated[DatabaseNotificationChannel, Depends(get_database_channel)],
) -> dict[str, int]:
    """Mark all notifications as read for current user."""
    count = await channel.mark_all_read(current_user.id)
    return {"marked_read": count}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    channel: Annotated[DatabaseNotificationChannel, Depends(get_database_channel)],
) -> dict[str, bool]:
    """Delete a single notification."""
    notification = await channel.get(str(notification_id))

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    success = await channel.delete_notification(str(notification_id))
    return {"success": success}


@router.delete("")
async def delete_read_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    channel: Annotated[DatabaseNotificationChannel, Depends(get_database_channel)],
) -> dict[str, int]:
    """Delete all read notifications for current user."""
    count = await channel.delete_read(current_user.id)
    return {"deleted": count}


# ============================================================
# ADMIN: BROADCAST NOTIFICATIONS
# ============================================================

@router.post("/broadcast", dependencies=[Depends(require_admin)])
async def broadcast_notification(
    request: BroadcastRequest,
    notifier: Annotated[Notifier, Depends(get_notifier)],
) -> BroadcastResult:
    """
    Broadcast notification to multiple users.

    Admin only. Sends to all specified users via selected channels.

    Example request:
    ```json
    {
        "user_ids": ["uuid1", "uuid2", "uuid3"],
        "notification": {
            "type": "info",
            "category": "system",
            "title": "Scheduled Maintenance",
            "message": "We will have maintenance tonight at 10 PM UTC"
        },
        "channels": ["in_app"]
    }
    ```
    """
    notification = create_notification(
        type=request.notification.type,
        category=request.notification.category,
        title=request.notification.title,
        message=request.notification.message,
        action_url=request.notification.action_url,
        action_label=request.notification.action_label,
        data=request.notification.data,
    )

    user_ids = [UUID(uid) for uid in request.user_ids]

    result = await notifier.broadcast(
        user_ids=user_ids,
        notification=notification,
        channels=request.channels,
    )

    return result


# ============================================================
# ADMIN: SEND TEST NOTIFICATION
# ============================================================

class TestNotificationRequest(BaseModel):
    """Request to send a test notification."""
    type: str = "info"
    category: str = "system"
    title: str = "Test Notification"
    message: str = "This is a test notification"
    action_url: Optional[str] = None


@router.post("/test", dependencies=[Depends(require_admin)])
async def send_test_notification(
    request: TestNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    notifier: Annotated[Notifier, Depends(get_notifier)],
) -> dict:
    """
    Send a test notification to the current admin user.

    Useful for testing notification setup.
    """
    notification = create_notification(
        type=request.type,
        category=request.category,
        title=request.title,
        message=request.message,
        action_url=request.action_url,
    )

    result = await notifier.notify(
        user_id=current_user.id,
        notification=notification,
        channels=["in_app"],
    )

    return {
        "success": result.success,
        "channels": result.channels,
        "errors": result.errors,
    }
