"""
Email tasks.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_email(
    self,
    to: list[str],
    subject: str,
    html: str,
    text: str | None = None,
):
    """
    Send an email.

    Args:
        to: List of recipient email addresses
        subject: Email subject
        html: HTML content
        text: Plain text content (optional)
    """
    try:
        logger.info(f"Sending email to {to}: {subject}")
        # TODO: Implement actual email sending
        # Use configured email backend
        return {"status": "sent", "recipients": to}
    except Exception as exc:
        logger.error(f"Failed to send email: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3)
def send_template_email(
    self,
    to: list[str],
    template_id: str,
    data: dict,
):
    """
    Send email using a template.

    Args:
        to: List of recipient email addresses
        template_id: Template identifier
        data: Template variables
    """
    try:
        logger.info(f"Sending template email {template_id} to {to}")
        # TODO: Load template, render, send
        return {"status": "sent", "template": template_id}
    except Exception as exc:
        logger.error(f"Failed to send template email: {exc}")
        raise self.retry(exc=exc)


@shared_task
def send_welcome_email(user_id: str, email: str, name: str):
    """Send welcome email to new user."""
    return send_template_email.delay(
        to=[email],
        template_id="welcome",
        data={"name": name, "user_id": user_id},
    )


@shared_task
def send_password_reset_email(email: str, reset_token: str):
    """Send password reset email."""
    return send_template_email.delay(
        to=[email],
        template_id="password_reset",
        data={"reset_token": reset_token},
    )
