"""
Organization routes.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.schemas.org import (
    OrgCreate,
    OrgUpdate,
    OrgResponse,
    OrgListResponse,
    OrgMemberResponse,
    AddMemberRequest,
    UpdateMemberRequest,
)
from src.services.org import OrgService
from src.api.dependencies.auth import get_current_user
from src.api.dependencies.services import get_org_service
from src.api.dependencies.permissions import require_org_permission
from src.models.user import User

router = APIRouter()


@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_org(
    data: OrgCreate,
    org_service: OrgService = Depends(get_org_service),
    current_user: User = Depends(get_current_user),
):
    """Create a new organization."""
    org = await org_service.create(data, owner_id=current_user.id)
    return OrgResponse.model_validate(org)


@router.get("", response_model=OrgListResponse)
async def list_orgs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    org_service: OrgService = Depends(get_org_service),
    current_user: User = Depends(get_current_user),
):
    """List organizations the user belongs to."""
    orgs, total = await org_service.list_for_user(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
    )
    return OrgListResponse(
        orgs=[OrgResponse.model_validate(o) for o in orgs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{org_id}", response_model=OrgResponse)
async def get_org(
    org_id: UUID,
    org_service: OrgService = Depends(get_org_service),
    _: User = Depends(require_org_permission("org:read")),
):
    """Get organization by ID."""
    org = await org_service.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return OrgResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrgResponse)
async def update_org(
    org_id: UUID,
    data: OrgUpdate,
    org_service: OrgService = Depends(get_org_service),
    _: User = Depends(require_org_permission("org:update")),
):
    """Update organization."""
    org = await org_service.update(org_id, data)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return OrgResponse.model_validate(org)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org(
    org_id: UUID,
    org_service: OrgService = Depends(get_org_service),
    _: User = Depends(require_org_permission("org:delete")),
):
    """Delete organization."""
    deleted = await org_service.delete(org_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


# Members
@router.get("/{org_id}/members", response_model=list[OrgMemberResponse])
async def list_members(
    org_id: UUID,
    org_service: OrgService = Depends(get_org_service),
    _: User = Depends(require_org_permission("org:read")),
):
    """List organization members."""
    members = await org_service.list_members(org_id)
    return [OrgMemberResponse.model_validate(m) for m in members]


@router.post("/{org_id}/members", response_model=OrgMemberResponse)
async def add_member(
    org_id: UUID,
    data: AddMemberRequest,
    org_service: OrgService = Depends(get_org_service),
    _: User = Depends(require_org_permission("org:members:manage")),
):
    """Add a member to organization."""
    member = await org_service.add_member(
        org_id=org_id,
        user_id=data.user_id,
        role=data.role,
    )
    return OrgMemberResponse.model_validate(member)


@router.patch("/{org_id}/members/{user_id}", response_model=OrgMemberResponse)
async def update_member(
    org_id: UUID,
    user_id: UUID,
    data: UpdateMemberRequest,
    org_service: OrgService = Depends(get_org_service),
    _: User = Depends(require_org_permission("org:members:manage")),
):
    """Update member role."""
    member = await org_service.update_member(
        org_id=org_id,
        user_id=user_id,
        role=data.role,
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return OrgMemberResponse.model_validate(member)


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    org_service: OrgService = Depends(get_org_service),
    _: User = Depends(require_org_permission("org:members:manage")),
):
    """Remove member from organization."""
    removed = await org_service.remove_member(org_id, user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
