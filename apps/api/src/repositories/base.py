"""
Base repository with common CRUD operations.
"""

from typing import TypeVar, Generic, Type, Any, Sequence
from uuid import UUID
from datetime import datetime
from sqlalchemy import Select, select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import Base
from src.utils.pagination import Page

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Base repository providing common CRUD operations.

    Usage:
        class UserRepository(BaseRepository[User]):
            model = User

        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)
        users = await repo.list(page=1, per_page=20)
    """

    model: Type[ModelT]

    def __init__(self, db: AsyncSession):
        self.db = db

    def _base_query(self) -> Select:
        """Base query - override to add default filters (e.g., soft delete)."""
        return select(self.model)

    async def get_by_id(self, id: UUID | str) -> ModelT | None:
        """Get entity by ID."""
        if isinstance(id, str):
            id = UUID(id)
        stmt = self._base_query().where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list[UUID]) -> list[ModelT]:
        """Get multiple entities by IDs."""
        stmt = self._base_query().where(self.model.id.in_(ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_one(self, **filters) -> ModelT | None:
        """Get single entity by filters."""
        stmt = self._base_query()
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, **filters) -> bool:
        """Check if entity exists."""
        stmt = select(func.count()).select_from(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        count = await self.db.scalar(stmt)
        return (count or 0) > 0

    async def count(self, **filters) -> int:
        """Count entities matching filters."""
        stmt = select(func.count()).select_from(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        return await self.db.scalar(stmt) or 0

    async def list(
        self,
        page: int = 1,
        per_page: int = 20,
        order_by: str | None = None,
        descending: bool = False,
        **filters,
    ) -> Page[ModelT]:
        """
        List entities with pagination and optional filters.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            order_by: Field name to order by
            descending: Order descending if True
            **filters: Field=value filters
        """
        stmt = self._base_query()

        # Apply filters
        for field, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, field) == value)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Apply ordering
        if order_by:
            column = getattr(self.model, order_by, None)
            if column is not None:
                stmt = stmt.order_by(column.desc() if descending else column)

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)

        # Execute
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return Page(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
        )

    async def all(self, **filters) -> list[ModelT]:
        """Get all entities matching filters (no pagination)."""
        stmt = self._base_query()
        for field, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, field) == value)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **data) -> ModelT:
        """Create new entity."""
        entity = self.model(**data)
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def create_many(self, items: list[dict]) -> list[ModelT]:
        """Create multiple entities."""
        entities = [self.model(**data) for data in items]
        self.db.add_all(entities)
        await self.db.flush()
        for entity in entities:
            await self.db.refresh(entity)
        return entities

    async def update(self, id: UUID, **data) -> ModelT | None:
        """Update entity by ID."""
        entity = await self.get_by_id(id)
        if not entity:
            return None

        for field, value in data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update_many(self, filters: dict, **data) -> int:
        """Update multiple entities matching filters."""
        stmt = (
            update(self.model)
            .where(*[getattr(self.model, k) == v for k, v in filters.items()])
            .values(**data)
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def delete(self, id: UUID) -> bool:
        """Delete entity by ID (hard delete)."""
        entity = await self.get_by_id(id)
        if not entity:
            return False
        await self.db.delete(entity)
        await self.db.flush()
        return True

    async def delete_many(self, **filters) -> int:
        """Delete multiple entities matching filters."""
        stmt = delete(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        result = await self.db.execute(stmt)
        return result.rowcount

    async def soft_delete(self, id: UUID) -> bool:
        """Soft delete entity (requires SoftDeleteMixin)."""
        entity = await self.get_by_id(id)
        if not entity:
            return False
        if hasattr(entity, "deleted_at"):
            entity.deleted_at = datetime.utcnow()
            await self.db.flush()
            return True
        return False


class SoftDeleteRepository(BaseRepository[ModelT]):
    """
    Repository that automatically filters out soft-deleted entities.

    Usage:
        class UserRepository(SoftDeleteRepository[User]):
            model = User
    """

    def _base_query(self) -> Select:
        """Exclude soft-deleted entities by default."""
        return select(self.model).where(self.model.deleted_at.is_(None))

    async def list_with_deleted(
        self,
        page: int = 1,
        per_page: int = 20,
        **filters,
    ) -> Page[ModelT]:
        """List including soft-deleted entities."""
        # Temporarily use base select without soft delete filter
        stmt = select(self.model)

        for field, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, field) == value)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)

        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return Page(items=items, total=total, page=page, per_page=per_page)

    async def restore(self, id: UUID) -> bool:
        """Restore soft-deleted entity."""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        entity = result.scalar_one_or_none()

        if not entity:
            return False

        if hasattr(entity, "deleted_at"):
            entity.deleted_at = None
            await self.db.flush()
            return True
        return False
