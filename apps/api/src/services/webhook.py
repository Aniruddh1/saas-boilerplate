"""Webhook service for managing and dispatching webhooks."""

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.webhook import Webhook, WebhookLog
from src.schemas.webhook import WebhookCreate, WebhookUpdate

logger = structlog.get_logger()

# Signature header name
SIGNATURE_HEADER = "X-Webhook-Signature"
TIMESTAMP_HEADER = "X-Webhook-Timestamp"
EVENT_HEADER = "X-Webhook-Event"


def generate_signature(payload: str, secret: str, timestamp: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    The signature is computed as: HMAC-SHA256(secret, timestamp + "." + payload)
    """
    message = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_signature(payload: str, secret: str, timestamp: str, signature: str) -> bool:
    """Verify a webhook signature."""
    expected = generate_signature(payload, secret, timestamp)
    return hmac.compare_digest(expected, signature)


class WebhookService:
    """Service for managing webhooks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, org_id: UUID, data: WebhookCreate) -> Webhook:
        """Create a new webhook."""
        webhook = Webhook(
            org_id=org_id,
            name=data.name,
            url=str(data.url),
            secret=data.secret,
            events=data.events,
            description=data.description,
            headers=data.headers,
            is_active=data.is_active,
            max_failures=data.max_failures,
        )
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def get(self, webhook_id: UUID) -> Optional[Webhook]:
        """Get a webhook by ID."""
        return await self.db.get(Webhook, webhook_id)

    async def get_by_org(self, org_id: UUID) -> list[Webhook]:
        """Get all webhooks for an organization."""
        result = await self.db.execute(
            select(Webhook).where(Webhook.org_id == org_id)
        )
        return list(result.scalars().all())

    async def update(self, webhook: Webhook, data: WebhookUpdate) -> Webhook:
        """Update a webhook."""
        update_data = data.model_dump(exclude_unset=True)
        if "url" in update_data and update_data["url"]:
            update_data["url"] = str(update_data["url"])

        for field, value in update_data.items():
            setattr(webhook, field, value)

        # Reset failure count if re-enabling
        if data.is_active and webhook.failure_count > 0:
            webhook.failure_count = 0

        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def delete(self, webhook: Webhook) -> None:
        """Delete a webhook."""
        await self.db.delete(webhook)
        await self.db.commit()

    async def get_logs(
        self,
        webhook_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> list[WebhookLog]:
        """Get logs for a webhook."""
        result = await self.db.execute(
            select(WebhookLog)
            .where(WebhookLog.webhook_id == webhook_id)
            .order_by(WebhookLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


class WebhookDispatcher:
    """
    Dispatches webhook events to registered endpoints.

    Usage:
        dispatcher = WebhookDispatcher(db)
        await dispatcher.dispatch(
            org_id=org.id,
            event_type="project.created",
            payload={"project": project_data}
        )
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.timeout = 10.0  # seconds

    async def dispatch(
        self,
        org_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        *,
        sync: bool = False
    ) -> None:
        """
        Dispatch an event to all subscribed webhooks.

        Args:
            org_id: Organization ID
            event_type: Type of event (e.g., "project.created")
            payload: Event payload data
            sync: If True, wait for all deliveries (use sparingly)
        """
        # Get active webhooks subscribed to this event
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.org_id == org_id,
                Webhook.is_active == True,
            )
        )
        webhooks = result.scalars().all()

        for webhook in webhooks:
            # Check if webhook is subscribed to this event
            if webhook.events and event_type not in webhook.events:
                continue

            if sync:
                await self._deliver(webhook, event_type, payload)
            else:
                # In production, queue this to a background worker
                # For now, deliver inline (you should use Celery/Redis queue)
                await self._deliver(webhook, event_type, payload)

    async def _deliver(
        self,
        webhook: Webhook,
        event_type: str,
        payload: dict[str, Any],
        attempt: int = 1
    ) -> bool:
        """Deliver a webhook event."""
        timestamp = str(int(time.time()))
        json_payload = json.dumps(payload, default=str, sort_keys=True)

        # Build headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SaaS-Webhook/1.0",
            EVENT_HEADER: event_type,
            TIMESTAMP_HEADER: timestamp,
        }

        # Add signature if secret is configured
        if webhook.secret:
            signature = generate_signature(json_payload, webhook.secret, timestamp)
            headers[SIGNATURE_HEADER] = signature

        # Add custom headers
        if webhook.headers:
            headers.update(webhook.headers)

        # Send request
        start_time = time.time()
        log = WebhookLog(
            webhook_id=webhook.id,
            event_type=event_type,
            payload=payload,
            request_headers={k: v for k, v in headers.items() if k != SIGNATURE_HEADER},
            attempt=attempt,
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    content=json_payload,
                    headers=headers,
                    timeout=self.timeout,
                )

            response_time = int((time.time() - start_time) * 1000)

            log.response_status = response.status_code
            log.response_body = response.text[:1000] if response.text else None
            log.response_time_ms = response_time
            log.success = 200 <= response.status_code < 300

            if log.success:
                # Reset failure count on success
                webhook.failure_count = 0
                webhook.last_triggered_at = datetime.now(timezone.utc)
            else:
                log.error_message = f"HTTP {response.status_code}"
                await self._handle_failure(webhook)

        except httpx.TimeoutException:
            log.error_message = "Request timeout"
            log.response_time_ms = int(self.timeout * 1000)
            await self._handle_failure(webhook)

        except httpx.RequestError as e:
            log.error_message = str(e)[:500]
            await self._handle_failure(webhook)

        except Exception as e:
            logger.exception("Webhook delivery error", webhook_id=str(webhook.id))
            log.error_message = str(e)[:500]
            await self._handle_failure(webhook)

        self.db.add(log)
        await self.db.commit()

        return log.success

    async def _handle_failure(self, webhook: Webhook) -> None:
        """Handle webhook delivery failure."""
        webhook.failure_count += 1

        if webhook.failure_count >= webhook.max_failures:
            webhook.is_active = False
            logger.warning(
                "Webhook auto-disabled due to failures",
                webhook_id=str(webhook.id),
                failure_count=webhook.failure_count,
            )

    async def test(self, webhook: Webhook) -> dict:
        """Send a test ping to a webhook."""
        timestamp = str(int(time.time()))
        payload = {
            "event": "test.ping",
            "webhook_id": str(webhook.id),
            "timestamp": timestamp,
            "message": "This is a test webhook delivery",
        }
        json_payload = json.dumps(payload, sort_keys=True)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SaaS-Webhook/1.0",
            EVENT_HEADER: "test.ping",
            TIMESTAMP_HEADER: timestamp,
        }

        if webhook.secret:
            signature = generate_signature(json_payload, webhook.secret, timestamp)
            headers[SIGNATURE_HEADER] = signature

        if webhook.headers:
            headers.update(webhook.headers)

        start_time = time.time()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    content=json_payload,
                    headers=headers,
                    timeout=self.timeout,
                )

            response_time = int((time.time() - start_time) * 1000)

            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "error": None,
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "status_code": None,
                "response_time_ms": int(self.timeout * 1000),
                "error": "Request timeout",
            }

        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e),
            }
