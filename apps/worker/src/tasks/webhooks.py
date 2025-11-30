"""
Webhook delivery tasks.
"""

import hmac
import hashlib
import logging
from datetime import datetime
import httpx
from celery import shared_task

from src.config import settings

logger = logging.getLogger(__name__)


def sign_payload(payload: str, secret: str) -> str:
    """Generate HMAC signature for webhook payload."""
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


@shared_task(
    bind=True,
    max_retries=5,
    autoretry_for=(httpx.HTTPError,),
    retry_backoff=True,
    retry_backoff_max=3600,
)
def deliver_webhook(
    self,
    webhook_id: str,
    url: str,
    payload: dict,
    secret: str | None = None,
    headers: dict | None = None,
):
    """
    Deliver a webhook to endpoint.

    Args:
        webhook_id: Unique webhook identifier
        url: Target URL
        payload: JSON payload to send
        secret: Secret for HMAC signature
        headers: Additional headers
    """
    import json

    payload_str = json.dumps(payload, default=str)
    request_headers = {
        "Content-Type": "application/json",
        "X-Webhook-ID": webhook_id,
        "X-Webhook-Timestamp": datetime.utcnow().isoformat(),
        **(headers or {}),
    }

    if secret:
        signature = sign_payload(payload_str, secret)
        request_headers["X-Webhook-Signature"] = f"sha256={signature}"

    try:
        with httpx.Client(timeout=settings.webhook_timeout) as client:
            response = client.post(
                url,
                content=payload_str,
                headers=request_headers,
            )
            response.raise_for_status()

        logger.info(f"Webhook {webhook_id} delivered to {url}")
        return {
            "status": "delivered",
            "webhook_id": webhook_id,
            "status_code": response.status_code,
        }

    except httpx.HTTPStatusError as exc:
        logger.warning(
            f"Webhook {webhook_id} failed with status {exc.response.status_code}"
        )
        raise

    except httpx.HTTPError as exc:
        logger.error(f"Webhook {webhook_id} delivery error: {exc}")
        raise


@shared_task
def process_webhook_batch(webhooks: list[dict]):
    """
    Process multiple webhooks.

    Args:
        webhooks: List of webhook configs with url, payload, secret
    """
    results = []
    for webhook in webhooks:
        result = deliver_webhook.delay(
            webhook_id=webhook.get("id"),
            url=webhook["url"],
            payload=webhook["payload"],
            secret=webhook.get("secret"),
            headers=webhook.get("headers"),
        )
        results.append(result.id)
    return results
