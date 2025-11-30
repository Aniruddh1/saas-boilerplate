"""Webhook API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_db
from src.models.user import User
from src.schemas.webhook import (
    WEBHOOK_EVENTS,
    WebhookCreate,
    WebhookLogResponse,
    WebhookResponse,
    WebhookTestResponse,
    WebhookUpdate,
)
from src.services.webhook import WebhookDispatcher, WebhookService

router = APIRouter(prefix="/orgs/{org_id}/webhooks", tags=["webhooks"])


async def get_webhook_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> WebhookService:
    return WebhookService(db)


async def get_webhook_dispatcher(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> WebhookDispatcher:
    return WebhookDispatcher(db)


@router.get("/events", response_model=list[str])
async def list_webhook_events():
    """List all available webhook event types."""
    return WEBHOOK_EVENTS


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[WebhookService, Depends(get_webhook_service)],
):
    """List all webhooks for an organization."""
    # TODO: Add permission check for org access
    webhooks = await service.get_by_org(org_id)
    return webhooks


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    org_id: UUID,
    data: WebhookCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[WebhookService, Depends(get_webhook_service)],
):
    """Create a new webhook."""
    # Validate event types
    invalid_events = set(data.events) - set(WEBHOOK_EVENTS)
    if invalid_events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event types: {invalid_events}",
        )

    webhook = await service.create(org_id, data)
    return webhook


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    org_id: UUID,
    webhook_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[WebhookService, Depends(get_webhook_service)],
):
    """Get a webhook by ID."""
    webhook = await service.get(webhook_id)
    if not webhook or webhook.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )
    return webhook


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    org_id: UUID,
    webhook_id: UUID,
    data: WebhookUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[WebhookService, Depends(get_webhook_service)],
):
    """Update a webhook."""
    webhook = await service.get(webhook_id)
    if not webhook or webhook.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # Validate event types if provided
    if data.events:
        invalid_events = set(data.events) - set(WEBHOOK_EVENTS)
        if invalid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event types: {invalid_events}",
            )

    webhook = await service.update(webhook, data)
    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    org_id: UUID,
    webhook_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[WebhookService, Depends(get_webhook_service)],
):
    """Delete a webhook."""
    webhook = await service.get(webhook_id)
    if not webhook or webhook.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    await service.delete(webhook)


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    org_id: UUID,
    webhook_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[WebhookService, Depends(get_webhook_service)],
    dispatcher: Annotated[WebhookDispatcher, Depends(get_webhook_dispatcher)],
):
    """Send a test ping to a webhook."""
    webhook = await service.get(webhook_id)
    if not webhook or webhook.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    result = await dispatcher.test(webhook)
    return WebhookTestResponse(**result)


@router.get("/{webhook_id}/logs", response_model=list[WebhookLogResponse])
async def list_webhook_logs(
    org_id: UUID,
    webhook_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[WebhookService, Depends(get_webhook_service)],
    limit: int = 50,
    offset: int = 0,
):
    """List delivery logs for a webhook."""
    webhook = await service.get(webhook_id)
    if not webhook or webhook.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    logs = await service.get_logs(webhook_id, limit=limit, offset=offset)
    return logs
