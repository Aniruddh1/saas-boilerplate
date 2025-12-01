"""
Project routes.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from src.services.project import ProjectService
from src.api.dependencies.auth import get_current_user
from src.api.dependencies.services import get_project_service
from src.api.dependencies.permissions import require_project_permission, require_org_permission
from src.models.user import User

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_org_permission("project:create")),
):
    """Create a new project."""
    project = await project_service.create(data, created_by=current_user.id)
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    org_id: UUID | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    """List projects accessible to user."""
    projects, total = await project_service.list_for_user(
        user_id=current_user.id,
        org_id=org_id,
        page=page,
        per_page=per_page,
    )
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    project_service: ProjectService = Depends(get_project_service),
    _: User = Depends(require_project_permission("project:read")),
):
    """Get project by ID."""
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    project_service: ProjectService = Depends(get_project_service),
    _: User = Depends(require_project_permission("project:update")),
):
    """Update project."""
    project = await project_service.update(project_id, data)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    project_service: ProjectService = Depends(get_project_service),
    _: User = Depends(require_project_permission("project:delete")),
):
    """Delete project."""
    deleted = await project_service.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
