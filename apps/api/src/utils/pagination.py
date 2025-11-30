"""
Pagination utilities for list endpoints.
"""

from typing import TypeVar, Generic, Sequence
from dataclasses import dataclass
from pydantic import BaseModel, Field
from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for pagination."""

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""

    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResponse[T]":
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            items=list(items),
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


@dataclass
class Page(Generic[T]):
    """Internal page result container."""

    items: list[T]
    total: int
    page: int
    per_page: int

    @property
    def pages(self) -> int:
        return (self.total + self.per_page - 1) // self.per_page if self.per_page > 0 else 0

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


class Paginator:
    """
    Paginator for SQLAlchemy queries.

    Usage:
        paginator = Paginator(db)
        page = await paginator.paginate(
            select(User).where(User.is_active == True),
            page=1,
            per_page=20,
        )
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def paginate(
        self,
        query: Select,
        page: int = 1,
        per_page: int = 20,
    ) -> Page:
        """
        Paginate a SQLAlchemy select query.

        Args:
            query: SQLAlchemy Select statement
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Page object with items, total, and pagination info
        """
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Apply pagination
        offset = (page - 1) * per_page
        paginated_query = query.offset(offset).limit(per_page)

        # Execute
        result = await self.db.execute(paginated_query)
        items = list(result.scalars().all())

        return Page(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
        )


# FastAPI dependency for pagination params
def get_pagination(
    page: int = 1,
    per_page: int = 20,
) -> PaginationParams:
    """FastAPI dependency for pagination parameters."""
    return PaginationParams(page=page, per_page=per_page)
