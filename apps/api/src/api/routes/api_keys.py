"""
API key management routes.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from src.schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreatedResponse,
    APIKeyListResponse,
)
from src.services.api_key import APIKeyService
from src.api.dependencies.auth import get_current_user
from src.api.dependencies.services import get_api_key_service
from src.api.dependencies.permissions import require_org_permission
from src.models.user import User

router = APIRouter()


@router.post("", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: APIKeyCreate,
    api_key_service: APIKeyService = Depends(get_api_key_service),
    current_user: User = Depends(require_org_permission("api_key:create")),
):
    """
    Create a new API key.

    Returns the full key only once - store it securely.
    """
    key, api_key = await api_key_service.create(
        data,
        created_by=current_user.id,
    )
    return APIKeyCreatedResponse(
        key=key,  # Full key, only shown once
        api_key=APIKeyResponse.model_validate(api_key),
    )


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    org_id: UUID | None = None,
    project_id: UUID | None = None,
    api_key_service: APIKeyService = Depends(get_api_key_service),
    current_user: User = Depends(get_current_user),
):
    """List API keys accessible to user."""
    keys = await api_key_service.list_for_user(
        user_id=current_user.id,
        org_id=org_id,
        project_id=project_id,
    )
    return APIKeyListResponse(
        api_keys=[APIKeyResponse.model_validate(k) for k in keys],
    )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: UUID,
    api_key_service: APIKeyService = Depends(get_api_key_service),
    _: User = Depends(require_org_permission("api_key:read")),
):
    """Get API key by ID."""
    key = await api_key_service.get_by_id(key_id)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return APIKeyResponse.model_validate(key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    api_key_service: APIKeyService = Depends(get_api_key_service),
    _: User = Depends(require_org_permission("api_key:delete")),
):
    """Revoke (delete) an API key."""
    revoked = await api_key_service.revoke(key_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/{key_id}/rotate", response_model=APIKeyCreatedResponse)
async def rotate_api_key(
    key_id: UUID,
    api_key_service: APIKeyService = Depends(get_api_key_service),
    current_user: User = Depends(require_org_permission("api_key:update")),
):
    """
    Rotate an API key (generate new key, invalidate old).

    Returns the new key - store it securely.
    """
    new_key, api_key = await api_key_service.rotate(key_id)
    if not new_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return APIKeyCreatedResponse(
        key=new_key,
        api_key=APIKeyResponse.model_validate(api_key),
    )
