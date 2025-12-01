# Notifications System

Enterprise-grade notification utilities with progressive complexity, supporting single notifications, multi-channel delivery, broadcast, and user preference management.

## Overview

| Level | Complexity | Use Case |
|-------|------------|----------|
| 1 | Simple | Single user, single channel |
| 2 | Multi-channel | Single user, multiple channels |
| 3 | Broadcast | Multiple users at once |
| 4 | Preference-aware | Respect user opt-in/out |
| 5 | Parallel | High-priority, all channels |

## Quick Start

### Level 1: Simple Notification

Send a notification to a single user.

```python
from src.utils.notifications import get_notifier, create_notification, Notifier
from fastapi import Depends

@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: str,
    notifier: Notifier = Depends(get_notifier),
    current_user: User = Depends(get_current_user),
):
    order = await confirm(order_id)

    # Send in-app notification
    await notifier.notify(
        current_user.id,
        create_notification(
            title="Order Confirmed",
            message=f"Your order #{order.number} has been confirmed",
            type="success",
            action_url=f"/orders/{order_id}",
        ),
    )

    return order
```

### Level 2: Multi-Channel Notification

Send to multiple channels simultaneously.

```python
@router.post("/payments")
async def process_payment(
    data: PaymentRequest,
    notifier: Notifier = Depends(get_notifier),
    current_user: User = Depends(get_current_user),
):
    payment = await charge(data)

    # Send via in-app AND email
    result = await notifier.notify(
        current_user.id,
        create_notification(
            title="Payment Received",
            message=f"We received your payment of ${payment.amount}",
            type="success",
            category="billing",
        ),
        channels=["in_app", "email"],
    )

    return payment
```

### Level 3: Broadcast to Many Users

Send the same notification to multiple users.

```python
@router.post("/admin/announcements")
async def create_announcement(
    data: AnnouncementRequest,
    notifier: Notifier = Depends(get_notifier),
    admin: AdminUser = Depends(get_admin_user),
):
    users = await get_all_active_users()

    result = await notifier.broadcast(
        [user.id for user in users],
        create_notification(
            title=data.title,
            message=data.message,
            type="info",
            category="system",
        ),
        channels=["in_app"],
    )

    return {
        "sent": result.successful,
        "failed": result.failed,
    }
```

### Level 4: Preference-Aware Notifications

Respect user notification preferences (opt-in/out per category).

```python
@router.post("/newsletter")
async def send_newsletter(
    content: str,
    notifier: Notifier = Depends(get_notifier),
    user_id: UUID = Depends(get_current_user_id),
):
    # Only sends if user has enabled marketing notifications
    result = await notifier.notify_preferred(
        user_id,
        create_notification(
            title="New Blog Post",
            message=content[:100] + "...",
            type="info",
            category="marketing",
            action_url="/blog/latest",
        ),
    )

    if not result.success:
        return {"sent": False, "reason": "User opted out"}

    return {"sent": True}
```

### Level 5: Parallel Multi-Channel (Urgent)

Send to all channels simultaneously for time-sensitive notifications.

```python
@router.post("/alerts/critical")
async def send_critical_alert(
    data: AlertRequest,
    notifier: Notifier = Depends(get_notifier),
):
    # Send to all channels in parallel for fastest delivery
    result = await notifier.notify_parallel(
        data.user_id,
        create_notification(
            title="Security Alert",
            message=data.message,
            type="error",
            category="security",
        ),
        channels=["in_app", "email", "webhook"],
    )

    return result
```

## Architecture

```
src/utils/notifications.py           # Notifier and utilities
src/core/interfaces/notifications.py # NotificationChannel protocol
src/implementations/notifications/
├── database.py                      # In-app (database) channel
├── email.py                         # Email channel
└── webhook.py                       # Webhook channel
src/models/notification.py           # Notification model
```

## Configuration

```env
# Available channels
NOTIFICATION_CHANNELS=in_app,email

# Email settings (for email channel)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=notifications@example.com
SMTP_PASSWORD=secret
```

## Notification Types

```python
from src.core.interfaces.notifications import NotificationType

NotificationType.INFO     # General information
NotificationType.SUCCESS  # Successful operations
NotificationType.WARNING  # Warnings
NotificationType.ERROR    # Errors/failures
```

## Notification Categories

```python
from src.core.interfaces.notifications import NotificationCategory

NotificationCategory.SYSTEM     # System notifications
NotificationCategory.BILLING    # Payment/subscription
NotificationCategory.SECURITY   # Security alerts
NotificationCategory.MARKETING  # Promotional (opt-in)
NotificationCategory.UPDATES    # Product updates
```

## Database Schema

```sql
-- Notifications table
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    type VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    action_url VARCHAR(500),
    action_label VARCHAR(100),
    data JSONB DEFAULT '{}',
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX ix_notifications_user_id ON notifications(user_id);
CREATE INDEX ix_notifications_user_unread ON notifications(user_id, read_at);
CREATE INDEX ix_notifications_user_category ON notifications(user_id, category);
CREATE INDEX ix_notifications_read_at ON notifications(read_at);

-- User preferences
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    category VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX ix_notification_prefs_unique
    ON notification_preferences(user_id, category, channel);
```

## API Endpoints

```python
# src/api/routes/notifications.py

@router.get("/notifications")
async def list_notifications(
    read: Optional[bool] = None,
    page: int = 1,
    size: int = 20,
    channel = Depends(get_database_channel),
    current_user: User = Depends(get_current_user),
):
    """List user's notifications with pagination."""
    notifications = await channel.list(
        current_user.id,
        read=read,
        skip=(page - 1) * size,
        limit=size,
    )
    total = await channel.count_total(current_user.id, read=read)
    return {
        "items": notifications,
        "total": total,
        "page": page,
        "size": size,
    }

@router.get("/notifications/unread-count")
async def get_unread_count(
    channel = Depends(get_database_channel),
    current_user: User = Depends(get_current_user),
):
    """Get count of unread notifications."""
    count = await channel.count_unread(current_user.id)
    return {"count": count}

@router.post("/notifications/{notification_id}/read")
async def mark_as_read(
    notification_id: UUID,
    channel = Depends(get_database_channel),
    current_user: User = Depends(get_current_user),
):
    """Mark notification as read."""
    await channel.mark_as_read(current_user.id, notification_id)
    return {"success": True}

@router.post("/notifications/read-all")
async def mark_all_as_read(
    channel = Depends(get_database_channel),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read."""
    count = await channel.mark_all_as_read(current_user.id)
    return {"marked": count}
```

## FastAPI Dependencies

```python
from src.utils.notifications import get_notifier, get_database_channel

# High-level Notifier (recommended)
@router.post("/send")
async def send_notification(
    data: NotificationCreate,
    notifier: Notifier = Depends(get_notifier),
):
    result = await notifier.notify(data.user_id, ...)
    return result

# Direct database channel access
@router.get("/notifications")
async def list_notifications(
    channel = Depends(get_database_channel),
):
    notifications = await channel.list(user_id, limit=20)
    return notifications
```

## User Preference Management

```python
# Get user preferences
prefs = await preferences_store.get(user_id)

# Check if channel is enabled for category
if prefs.is_enabled("billing", "email"):
    await send_billing_email(...)

# Update preference
await preferences_store.set(
    user_id,
    category="marketing",
    channel="email",
    enabled=False,  # User opts out of marketing emails
)
```

## Implementing Custom Channels

```python
from src.core.interfaces.notifications import NotificationChannel, NotificationResult

class SlackNotificationChannel(NotificationChannel):
    """Send notifications to Slack."""

    async def send(
        self,
        user_id: UUID,
        notification: Notification,
    ) -> NotificationResult:
        slack_user = await get_slack_user(user_id)

        response = await slack_client.post_message(
            channel=slack_user.dm_channel,
            text=f"*{notification.title}*\n{notification.message}",
        )

        return NotificationResult(
            success=response.ok,
            channel="slack",
            notification_id=response.ts,
        )

    async def send_bulk(
        self,
        user_ids: list[UUID],
        notification: Notification,
    ) -> BulkNotificationResult:
        results = await asyncio.gather(*[
            self.send(uid, notification) for uid in user_ids
        ], return_exceptions=True)

        sent = sum(1 for r in results if isinstance(r, NotificationResult) and r.success)
        return BulkNotificationResult(sent=sent, failed=len(user_ids) - sent)

    async def health_check(self) -> bool:
        return await slack_client.test_connection()
```

Register the channel:

```python
notifier = Notifier(
    channels={
        "in_app": DatabaseNotificationChannel(db),
        "email": EmailNotificationChannel(smtp),
        "slack": SlackNotificationChannel(slack_client),
    }
)
```

## Pattern Selection Guide

| Pattern | Use When | Example |
|---------|----------|---------|
| Single | One user, one channel | Order confirmations |
| Multi-channel | One user, ensure delivery | Payment receipts |
| Broadcast | Same message to many | System announcements |
| Preference-aware | User-controlled categories | Marketing, newsletters |
| Parallel | Time-critical alerts | Security alerts |

## Best Practices

1. **Categorize notifications** - Use appropriate categories for user preferences
2. **Respect preferences** - Always check opt-in for non-critical notifications
3. **Keep messages concise** - Clear titles, brief messages
4. **Include actions** - Add `action_url` for notifications that need user action
5. **Monitor delivery** - Log and track notification delivery rates
6. **Rate limit broadcasts** - Don't spam users with too many notifications
7. **Clean up old notifications** - Schedule cleanup of read notifications

## Testing

```python
import pytest
from src.utils.notifications import Notifier, create_notification

class MockChannel:
    def __init__(self):
        self.sent = []

    async def send(self, user_id, notification):
        self.sent.append((user_id, notification))
        return NotificationResult(success=True, channel="mock")

    async def send_bulk(self, user_ids, notification):
        for uid in user_ids:
            self.sent.append((uid, notification))
        return BulkNotificationResult(sent=len(user_ids), failed=0)

@pytest.fixture
def notifier():
    mock = MockChannel()
    return Notifier(channels={"mock": mock})

async def test_notify(notifier):
    result = await notifier.notify(
        user_id,
        create_notification("Test", "Message"),
        channels=["mock"],
    )
    assert result.success
    assert result.channels["mock"] is True
```
