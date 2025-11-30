"""
User service.
"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.user import User
from src.schemas.user import UserUpdate
from src.core.hooks.manager import hooks


class UserService:
    """User management service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID | str) -> User | None:
        """Get user by ID."""
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(
        self,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        """List users with pagination."""
        stmt = select(User)

        if search:
            stmt = stmt.where(
                User.email.ilike(f"%{search}%") |
                User.name.ilike(f"%{search}%")
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        users = list(result.scalars().all())

        return users, total

    async def update(self, user_id: UUID, data: UserUpdate) -> User | None:
        """Update user."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        await hooks.trigger("user.updated", user=user)

        return user

    async def delete(self, user_id: UUID) -> bool:
        """Delete user."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        await hooks.trigger("user.deleted", user=user)
        await self.db.delete(user)
        await self.db.flush()

        return True
