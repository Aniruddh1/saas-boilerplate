"""
Enterprise Pagination Utilities.

Supports:
- Offset pagination (page/per_page) - best for UI tables
- Cursor pagination (cursor/limit) - best for infinite scroll, real-time data
- Streaming/Export - best for bulk data operations
- Count-only queries - best for UI badges

Usage:
    # Offset pagination (default)
    GET /users?page=1&per_page=20

    # Cursor pagination
    GET /users?cursor=abc123&limit=20

    # Export mode
    GET /users/export?format=csv

    # Count only
    GET /users/count
"""

import base64
import json
from datetime import datetime
from enum import Enum
from typing import TypeVar, Generic, Sequence, Any, AsyncIterator, Callable, Optional
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Query
from fastapi.responses import StreamingResponse

T = TypeVar("T")


# ============================================================
# PAGINATION MODES
# ============================================================

class PaginationMode(str, Enum):
    """Pagination strategy."""
    OFFSET = "offset"  # page/per_page
    CURSOR = "cursor"  # cursor/limit


# ============================================================
# OFFSET PAGINATION (Traditional)
# ============================================================

class OffsetParams(BaseModel):
    """Offset pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


class OffsetPage(BaseModel, Generic[T]):
    """Offset pagination response."""

    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "OffsetPage[T]":
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            items=list(items),
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )


# ============================================================
# CURSOR PAGINATION (Keyset)
# ============================================================

class CursorParams(BaseModel):
    """Cursor pagination parameters."""

    cursor: Optional[str] = Field(default=None, description="Opaque cursor for next page")
    limit: int = Field(default=20, ge=1, le=100, description="Number of items")
    direction: str = Field(default="next", pattern="^(next|prev)$")


class CursorPage(BaseModel, Generic[T]):
    """Cursor pagination response."""

    items: list[T]
    next_cursor: Optional[str]
    prev_cursor: Optional[str]
    has_next: bool
    has_prev: bool
    limit: int

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        next_cursor: Optional[str],
        prev_cursor: Optional[str],
        limit: int,
    ) -> "CursorPage[T]":
        return cls(
            items=list(items),
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=next_cursor is not None,
            has_prev=prev_cursor is not None,
            limit=limit,
        )


def encode_cursor(data: dict[str, Any]) -> str:
    """Encode cursor data to opaque string."""
    json_str = json.dumps(data, default=str, sort_keys=True)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode opaque cursor string to data."""
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        return json.loads(json_str)
    except Exception:
        return {}


# ============================================================
# UNIFIED PAGINATOR
# ============================================================

class Paginator:
    """
    Unified paginator supporting both offset and cursor modes.

    Usage:
        paginator = Paginator(db)

        # Offset pagination
        page = await paginator.paginate_offset(
            select(User).where(User.is_active == True),
            page=1,
            per_page=20,
        )

        # Cursor pagination
        page = await paginator.paginate_cursor(
            select(User),
            cursor="abc123",
            limit=20,
            order_by="created_at",
            order_column=User.created_at,
            id_column=User.id,
        )
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Offset Pagination ---

    async def paginate_offset(
        self,
        query: Select,
        page: int = 1,
        per_page: int = 20,
    ) -> OffsetPage:
        """
        Paginate using offset/limit (traditional).

        Best for:
        - Admin tables with page numbers
        - Known total count needed
        - Random page access (jump to page 5)
        """
        # Count total
        count_query = Select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Apply pagination
        offset = (page - 1) * per_page
        paginated_query = query.offset(offset).limit(per_page)

        # Execute
        result = await self.db.execute(paginated_query)
        items = list(result.scalars().all())

        return OffsetPage.create(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
        )

    # --- Cursor Pagination ---

    async def paginate_cursor(
        self,
        query: Select,
        cursor: Optional[str],
        limit: int,
        order_column: Any,
        id_column: Any,
        descending: bool = True,
    ) -> CursorPage:
        """
        Paginate using cursor/keyset.

        Best for:
        - Infinite scroll
        - Real-time feeds (new items added)
        - Large datasets (no COUNT query)
        - Consistent results during pagination

        Args:
            query: Base query
            cursor: Opaque cursor from previous response
            limit: Number of items
            order_column: Column to order by (e.g., User.created_at)
            id_column: ID column for tie-breaking (e.g., User.id)
            descending: Sort order (True = newest first)
        """
        order_func = desc if descending else asc

        # Apply ordering
        ordered_query = query.order_by(order_func(order_column), order_func(id_column))

        # Apply cursor filter if provided
        if cursor:
            cursor_data = decode_cursor(cursor)
            order_value = cursor_data.get("v")
            id_value = cursor_data.get("id")

            if order_value is not None and id_value is not None:
                if descending:
                    ordered_query = ordered_query.where(
                        (order_column < order_value) |
                        ((order_column == order_value) & (id_column < id_value))
                    )
                else:
                    ordered_query = ordered_query.where(
                        (order_column > order_value) |
                        ((order_column == order_value) & (id_column > id_value))
                    )

        # Fetch one extra to check for next page
        result = await self.db.execute(ordered_query.limit(limit + 1))
        items = list(result.scalars().all())

        # Determine if there's a next page
        has_next = len(items) > limit
        if has_next:
            items = items[:limit]

        # Build cursors
        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            next_cursor = encode_cursor({
                "v": getattr(last_item, order_column.key),
                "id": str(getattr(last_item, id_column.key)),
            })

        prev_cursor = None
        if cursor and items:
            first_item = items[0]
            prev_cursor = encode_cursor({
                "v": getattr(first_item, order_column.key),
                "id": str(getattr(first_item, id_column.key)),
                "dir": "prev",
            })

        return CursorPage.create(
            items=items,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            limit=limit,
        )

    # --- Count Only ---

    async def count(self, query: Select) -> int:
        """Get count without fetching items."""
        count_query = Select(func.count()).select_from(query.subquery())
        return await self.db.scalar(count_query) or 0


# ============================================================
# STREAMING / EXPORT
# ============================================================

class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"  # JSON Lines (one JSON object per line)


async def stream_query(
    db: AsyncSession,
    query: Select,
    batch_size: int = 1000,
) -> AsyncIterator[Any]:
    """
    Stream query results in batches.

    Best for:
    - Large data exports
    - Memory-efficient processing
    - Background jobs

    Usage:
        async for item in stream_query(db, select(User)):
            process(item)
    """
    offset = 0
    while True:
        result = await db.execute(query.offset(offset).limit(batch_size))
        items = list(result.scalars().all())

        if not items:
            break

        for item in items:
            yield item

        if len(items) < batch_size:
            break

        offset += batch_size


def create_csv_streaming_response(
    items_iterator: AsyncIterator[Any],
    serializer: Callable[[Any], dict],
    filename: str = "export.csv",
) -> StreamingResponse:
    """
    Create a streaming CSV response.

    Args:
        items_iterator: Async iterator of items
        serializer: Function to convert item to dict
        filename: Download filename
    """
    import csv
    import io

    async def generate():
        headers_written = False
        buffer = io.StringIO()
        writer = None

        async for item in items_iterator:
            row = serializer(item)

            if not headers_written:
                writer = csv.DictWriter(buffer, fieldnames=row.keys())
                writer.writeheader()
                headers_written = True
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate()

            writer.writerow(row)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def create_jsonl_streaming_response(
    items_iterator: AsyncIterator[Any],
    serializer: Callable[[Any], dict],
    filename: str = "export.jsonl",
) -> StreamingResponse:
    """
    Create a streaming JSON Lines response.

    Each line is a valid JSON object. Better for large datasets
    than a single JSON array.
    """
    async def generate():
        async for item in items_iterator:
            row = serializer(item)
            yield json.dumps(row, default=str) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/jsonl",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ============================================================
# FASTAPI DEPENDENCIES
# ============================================================

def get_offset_params(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> OffsetParams:
    """FastAPI dependency for offset pagination."""
    return OffsetParams(page=page, per_page=per_page)


def get_cursor_params(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Number of items"),
) -> CursorParams:
    """FastAPI dependency for cursor pagination."""
    return CursorParams(cursor=cursor, limit=limit)


# ============================================================
# LEGACY ALIASES (backward compatibility)
# ============================================================

# Keep old names working
PaginationParams = OffsetParams
PaginatedResponse = OffsetPage
Page = OffsetPage

def get_pagination(
    page: int = 1,
    per_page: int = 20,
) -> OffsetParams:
    """Legacy alias for get_offset_params."""
    return OffsetParams(page=page, per_page=per_page)
