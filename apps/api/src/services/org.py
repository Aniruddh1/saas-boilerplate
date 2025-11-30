"""
Organization service.
"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.models.org import Organization, OrgMember, OrgRole
from src.schemas.org import OrgCreate, OrgUpdate
from src.core.hooks.manager import hooks


class OrgService:
    """Organization management service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, org_id: UUID) -> Organization | None:
        """Get organization by ID."""
        stmt = select(Organization).where(Organization.id == org_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        """Get organization by slug."""
        stmt = select(Organization).where(Organization.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: OrgCreate, owner_id: UUID) -> Organization:
        """Create organization with owner."""
        # Check slug uniqueness
        if await self.get_by_slug(data.slug):
            raise ValueError("Organization slug already exists")

        org = Organization(**data.model_dump())
        self.db.add(org)
        await self.db.flush()

        # Add owner as member
        member = OrgMember(
            org_id=org.id,
            user_id=owner_id,
            role=OrgRole.OWNER,
        )
        self.db.add(member)
        await self.db.flush()

        await hooks.trigger("org.created", org=org, owner_id=owner_id)

        return org

    async def update(self, org_id: UUID, data: OrgUpdate) -> Organization | None:
        """Update organization."""
        org = await self.get_by_id(org_id)
        if not org:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(org, field, value)

        await self.db.flush()
        return org

    async def delete(self, org_id: UUID) -> bool:
        """Delete organization."""
        org = await self.get_by_id(org_id)
        if not org:
            return False

        await self.db.delete(org)
        await self.db.flush()
        return True

    async def list_for_user(
        self,
        user_id: UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Organization], int]:
        """List organizations user belongs to."""
        stmt = (
            select(Organization)
            .join(OrgMember)
            .where(OrgMember.user_id == user_id)
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        orgs = list(result.scalars().all())

        return orgs, total

    # Members
    async def list_members(self, org_id: UUID) -> list[OrgMember]:
        """List organization members with user info."""
        stmt = (
            select(OrgMember)
            .where(OrgMember.org_id == org_id)
            .options(selectinload(OrgMember.user))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_member(
        self,
        org_id: UUID,
        user_id: UUID,
        role: OrgRole = OrgRole.MEMBER,
    ) -> OrgMember:
        """Add member to organization."""
        member = OrgMember(org_id=org_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.flush()
        # Reload with user relationship
        await self.db.refresh(member)
        stmt = (
            select(OrgMember)
            .where(OrgMember.id == member.id)
            .options(selectinload(OrgMember.user))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def update_member(
        self,
        org_id: UUID,
        user_id: UUID,
        role: OrgRole,
    ) -> OrgMember | None:
        """Update member role."""
        stmt = (
            select(OrgMember)
            .where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
            .options(selectinload(OrgMember.user))
        )
        result = await self.db.execute(stmt)
        member = result.scalar_one_or_none()

        if not member:
            return None

        member.role = role
        await self.db.flush()
        return member

    async def remove_member(self, org_id: UUID, user_id: UUID) -> bool:
        """Remove member from organization."""
        stmt = select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        member = result.scalar_one_or_none()

        if not member:
            return False

        await self.db.delete(member)
        await self.db.flush()
        return True
