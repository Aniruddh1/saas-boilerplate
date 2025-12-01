"""
Webhook notification channel - sends notifications to external webhook endpoints.
"""

from __future__ import annotations

import hmac
import hashlib
import json
from datetime import datetime
from uuid import UUID
from typing import Optional, Callable, Awaitable

import httpx

from src.core.interfaces.notifications import (
    Notification,
    NotificationResult,
    BulkNotificationResult,
)


# Type for webhook URL lookup function
WebhookLookup = Callable[[UUID], Awaitable[Optional[dict]]]


class WebhookNotificationChannel:
    """
    Webhook notification channel.

    Sends notifications as HTTP POST requests to configured webhook URLs.
    Supports HMAC signature verification for security.

    Usage:
        channel = WebhookNotificationChannel(
            webhook_lookup=get_user_webhook,
            secret="your-webhook-secret",
        )

        result = await channel.send(user_id, notification)
    """

    channel_type = "webhook"

    def __init__(
        self,
        webhook_lookup: WebhookLookup,
        secret: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize webhook channel.

        Args:
            webhook_lookup: Async function to get webhook URL/config by user ID
            secret: Secret for HMAC signature (recommended for security)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.webhook_lookup = webhook_lookup
        self.secret = secret
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def send(
        self,
        user_id: UUID,
        notification: Notification,
    ) -> NotificationResult:
        """
        Send notification to webhook endpoint.
        """
        try:
            # Look up webhook configuration
            webhook_config = await self.webhook_lookup(user_id)
            if not webhook_config or not webhook_config.get("url"):
                return NotificationResult(
                    success=False,
                    channel=self.channel_type,
                    error="Webhook URL not configured for user",
                )

            url = webhook_config["url"]
            custom_headers = webhook_config.get("headers", {})

            # Build payload
            payload = self._build_payload(user_id, notification)
            payload_json = json.dumps(payload, default=str)

            # Build headers
            headers = {
                "Content-Type": "application/json",
                "X-Notification-Type": notification.type.value,
                "X-Notification-Category": notification.category.value,
                **custom_headers,
            }

            # Add HMAC signature if secret configured
            if self.secret:
                signature = self._sign_payload(payload_json)
                headers["X-Webhook-Signature"] = f"sha256={signature}"

            # Send request with retries
            last_error = None
            for attempt in range(self.max_retries):
                try:
                    response = await self._client.post(
                        url,
                        content=payload_json,
                        headers=headers,
                    )

                    if response.status_code >= 200 and response.status_code < 300:
                        return NotificationResult(
                            success=True,
                            channel=self.channel_type,
                            provider_response={
                                "status_code": response.status_code,
                                "response": response.text[:500],  # Limit response size
                            },
                        )
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text[:200]}"

                except httpx.RequestError as e:
                    last_error = str(e)

            return NotificationResult(
                success=False,
                channel=self.channel_type,
                error=last_error or "Unknown error",
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
        Send notification to multiple users' webhooks.
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
        """Check HTTP client health."""
        try:
            # Basic check - can we create HTTP requests
            return self._client is not None
        except Exception:
            return False

    def _build_payload(
        self,
        user_id: UUID,
        notification: Notification,
    ) -> dict:
        """Build webhook payload."""
        return {
            "event": "notification",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(user_id),
            "notification": {
                "type": notification.type.value,
                "category": notification.category.value,
                "title": notification.title,
                "message": notification.message,
                "action_url": notification.action_url,
                "action_label": notification.action_label,
                "data": notification.data,
            },
        }

    def _sign_payload(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature for payload."""
        if not self.secret:
            return ""

        signature = hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return signature

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "WebhookNotificationChannel":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
