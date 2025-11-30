"""
Project service.
"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.project import Project
from src.models.org import OrgMember
from src.schemas.project import ProjectCreate, ProjectUpdate
from src.core.hooks.manager import hooks


class ProjectService:
    """Project management service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id: UUID) -> Project | None:
        """Get project by ID."""
        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: ProjectCreate, created_by: UUID) -> Project:
        """Create project."""
        project = Project(**data.model_dump())
        self.db.add(project)
        await self.db.flush()

        await hooks.trigger("project.created", project=project, created_by=created_by)

        return project

    async def update(self, project_id: UUID, data: ProjectUpdate) -> Project | None:
        """Update project."""
        project = await self.get_by_id(project_id)
        if not project:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        await self.db.flush()
        return project

    async def delete(self, project_id: UUID) -> bool:
        """Delete project."""
        project = await self.get_by_id(project_id)
        if not project:
            return False

        await self.db.delete(project)
        await self.db.flush()
        return True

    async def list_for_user(
        self,
        user_id: UUID,
        org_id: UUID | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Project], int]:
        """List projects accessible to user."""
        # Get orgs user belongs to
        stmt = (
            select(Project)
            .join(OrgMember, Project.org_id == OrgMember.org_id)
            .where(OrgMember.user_id == user_id)
        )

        if org_id:
            stmt = stmt.where(Project.org_id == org_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        projects = list(result.scalars().all())

        return projects, total
