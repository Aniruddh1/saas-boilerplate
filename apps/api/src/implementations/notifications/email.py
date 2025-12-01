"""
Email notification channel - sends notifications via email.
"""

from __future__ import annotations

from html import escape as html_escape
from uuid import UUID
from typing import Optional, Callable, Awaitable

from src.core.interfaces.notifications import (
    Notification,
    NotificationResult,
    BulkNotificationResult,
)
from src.core.interfaces.email import EmailBackend, EmailMessage, EmailAddress


# Type for user lookup function
UserLookup = Callable[[UUID], Awaitable[Optional[dict]]]


class EmailNotificationChannel:
    """
    Email notification channel.

    Sends notifications as emails using the configured email backend.

    Usage:
        channel = EmailNotificationChannel(
            email_backend=email,
            user_lookup=get_user_email,
        )

        result = await channel.send(user_id, notification)
    """

    channel_type = "email"

    def __init__(
        self,
        email_backend: EmailBackend,
        user_lookup: UserLookup,
        from_address: Optional[EmailAddress] = None,
        template_id: Optional[str] = None,
    ):
        """
        Initialize email channel.

        Args:
            email_backend: Email backend for sending
            user_lookup: Async function to get user email by ID
            from_address: Default from address
            template_id: Optional email template ID for formatted notifications
        """
        self.email = email_backend
        self.user_lookup = user_lookup
        self.from_address = from_address or EmailAddress(
            email="notifications@example.com",
            name="Notifications",
        )
        self.template_id = template_id

    async def send(
        self,
        user_id: UUID,
        notification: Notification,
    ) -> NotificationResult:
        """
        Send notification as email.
        """
        try:
            # Look up user email
            user = await self.user_lookup(user_id)
            if not user or not user.get("email"):
                return NotificationResult(
                    success=False,
                    channel=self.channel_type,
                    error="User email not found",
                )

            # Build email message
            to_address = EmailAddress(
                email=user["email"],
                name=user.get("name"),
            )

            # Use template if configured
            if self.template_id:
                result = await self.email.send_template(
                    template_id=self.template_id,
                    to=[to_address],
                    data={
                        "type": notification.type.value,
                        "category": notification.category.value,
                        "title": notification.title,
                        "message": notification.message,
                        "action_url": notification.action_url,
                        "action_label": notification.action_label,
                        **notification.data,
                    },
                    from_address=self.from_address,
                )
            else:
                # Build plain email
                html = self._build_html(notification)
                message = EmailMessage(
                    to=[to_address],
                    subject=notification.title,
                    html=html,
                    text=notification.message,
                    from_address=self.from_address,
                    tags=["notification", notification.category.value],
                )
                result = await self.email.send(message)

            return NotificationResult(
                success=result.status.value in ("sent", "delivered"),
                channel=self.channel_type,
                notification_id=result.message_id,
                error=result.error,
            )

        except Exception as e:
            return NotificationResult(
                success=False,
                channel=self.channel_type,
                error=str(e),
            )

    async def send_bulk(
        self,
        user_ids: list[UUID],
        notification: Notification,
    ) -> BulkNotificationResult:
        """
        Send notification to multiple users via email.
        """
        results = []
        sent = 0
        failed = 0

        for user_id in user_ids:
            result = await self.send(user_id, notification)
            results.append(result)
            if result.success:
                sent += 1
            else:
                failed += 1

        return BulkNotificationResult(
            total=len(user_ids),
            sent=sent,
            failed=failed,
            results=results,
        )

    async def health_check(self) -> bool:
        """Check email backend health."""
        try:
            # Check if we can get stats (basic connectivity test)
            await self.email.get_stats(days=1)
            return True
        except Exception:
            return False

    def _build_html(self, notification: Notification) -> str:
        """Build HTML email from notification."""
        # Escape user-controlled content to prevent XSS
        title = html_escape(notification.title)
        message = html_escape(notification.message)

        action_html = ""
        if notification.action_url:
            # Escape URL and label
            action_url = html_escape(notification.action_url)
            label = html_escape(notification.action_label or "View Details")
            action_html = f"""
            <p style="margin-top: 20px;">
                <a href="{action_url}"
                   style="background-color: #4F46E5; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    {label}
                </a>
            </p>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                     line-height: 1.6; color: #374151; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f9fafb; border-radius: 8px; padding: 24px;">
                <h1 style="color: #111827; font-size: 24px; margin: 0 0 16px 0;">
                    {title}
                </h1>
                <p style="margin: 0; font-size: 16px;">
                    {message}
                </p>
                {action_html}
            </div>
            <p style="color: #9ca3af; font-size: 12px; margin-top: 24px; text-align: center;">
                You received this notification because of your account settings.
            </p>
        </body>
        </html>
        """
