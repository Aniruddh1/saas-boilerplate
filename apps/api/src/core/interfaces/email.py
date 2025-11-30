"""
Email backend protocol.
Implementations: SMTPBackend, SendGridBackend, PostmarkBackend, SESBackend, ResendBackend
"""
from __future__ import annotations

from typing import Protocol, Any
from dataclasses import dataclass, field
from enum import Enum


class EmailStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    FAILED = "failed"


@dataclass
class EmailAddress:
    """Email address with optional name."""
    email: str
    name: str | None = None

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


@dataclass
class Attachment:
    """Email attachment."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    content_id: str | None = None  # For inline images


@dataclass
class EmailMessage:
    """Email message to send."""
    to: list[EmailAddress]
    subject: str

    # Content (at least one required)
    html: str | None = None
    text: str | None = None

    # Optional fields
    from_address: EmailAddress | None = None  # Uses default if not set
    reply_to: EmailAddress | None = None
    cc: list[EmailAddress] = field(default_factory=list)
    bcc: list[EmailAddress] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)  # For analytics
    metadata: dict[str, str] = field(default_factory=dict)  # Custom data

    # Template support
    template_id: str | None = None
    template_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailResult:
    """Result of sending an email."""
    message_id: str
    status: EmailStatus
    error: str | None = None
    provider_response: dict[str, Any] | None = None


@dataclass
class BulkEmailResult:
    """Result of bulk email send."""
    total: int
    sent: int
    failed: int
    results: list[EmailResult]


class EmailBackend(Protocol):
    """
    Protocol for email backends.

    Example implementations:
    - SMTPBackend: Standard SMTP
    - SendGridBackend: SendGrid API
    - PostmarkBackend: Postmark API
    - SESBackend: AWS SES
    - ResendBackend: Resend API
    - ConsoleBackend: Print to console (dev/testing)
    """

    async def send(self, message: EmailMessage) -> EmailResult:
        """Send a single email."""
        ...

    async def send_bulk(
        self,
        messages: list[EmailMessage],
    ) -> BulkEmailResult:
        """Send multiple emails in batch."""
        ...

    async def send_template(
        self,
        template_id: str,
        to: list[EmailAddress],
        data: dict[str, Any],
        from_address: EmailAddress | None = None,
        subject: str | None = None,  # Override template subject
    ) -> EmailResult:
        """Send using a provider template."""
        ...

    # Webhook handling
    async def process_webhook(
        self,
        payload: dict[str, Any],
        signature: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Process delivery webhook from provider.
        Returns list of events (delivered, bounced, etc.).
        """
        ...

    # Optional: Template management (if provider supports)
    async def create_template(
        self,
        name: str,
        subject: str,
        html: str,
        text: str | None = None,
    ) -> str:
        """Create email template. Returns template_id."""
        ...

    async def update_template(
        self,
        template_id: str,
        subject: str | None = None,
        html: str | None = None,
        text: str | None = None,
    ) -> bool:
        """Update existing template."""
        ...

    async def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        ...

    async def list_templates(self) -> list[dict[str, Any]]:
        """List all templates."""
        ...

    # Stats
    async def get_stats(
        self,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get sending statistics."""
        ...
