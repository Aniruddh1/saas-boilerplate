"""
Search backend protocol.
Implementations: MeilisearchBackend, TypesenseBackend, ElasticsearchBackend
"""
from __future__ import annotations

from typing import Protocol, Any, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class SearchFilter:
    """Search filter condition."""
    field: str
    operator: str  # "=", "!=", ">", ">=", "<", "<=", "in", "contains"
    value: Any


@dataclass
class SearchQuery:
    """Search query parameters."""
    q: str = ""  # Search query string
    filters: list[SearchFilter] = field(default_factory=list)
    sort: list[tuple[str, SortOrder]] = field(default_factory=list)
    facets: list[str] = field(default_factory=list)
    page: int = 1
    per_page: int = 20
    attributes_to_retrieve: list[str] | None = None
    attributes_to_highlight: list[str] | None = None


@dataclass
class FacetCount:
    """Facet value and count."""
    value: str
    count: int


@dataclass
class SearchHit:
    """Single search result."""
    id: str
    score: float
    document: dict[str, Any]
    highlights: dict[str, str] | None = None


@dataclass
class SearchResult:
    """Search results with metadata."""
    hits: list[SearchHit]
    total: int
    page: int
    per_page: int
    total_pages: int
    facets: dict[str, list[FacetCount]] = field(default_factory=dict)
    query_time_ms: int = 0


@dataclass
class IndexSchema:
    """Schema for a search index."""
    name: str
    primary_key: str = "id"
    searchable_fields: list[str] = field(default_factory=list)
    filterable_fields: list[str] = field(default_factory=list)
    sortable_fields: list[str] = field(default_factory=list)
    facet_fields: list[str] = field(default_factory=list)


T = TypeVar("T")


class SearchBackend(Protocol):
    """
    Protocol for search backends.

    Example implementations:
    - MeilisearchBackend: Meilisearch
    - TypesenseBackend: Typesense
    - ElasticsearchBackend: Elasticsearch/OpenSearch
    - PostgresSearchBackend: PostgreSQL full-text search
    """

    # Index management
    async def create_index(self, schema: IndexSchema) -> bool:
        """Create a new search index."""
        ...

    async def delete_index(self, name: str) -> bool:
        """Delete an index."""
        ...

    async def index_exists(self, name: str) -> bool:
        """Check if index exists."""
        ...

    async def list_indexes(self) -> list[str]:
        """List all index names."""
        ...

    async def update_schema(self, schema: IndexSchema) -> bool:
        """Update index schema/settings."""
        ...

    # Document operations
    async def index_document(
        self,
        index: str,
        document: dict[str, Any],
        id: str | None = None,
    ) -> str:
        """Index a single document. Returns document ID."""
        ...

    async def index_documents(
        self,
        index: str,
        documents: list[dict[str, Any]],
    ) -> tuple[int, list[str]]:
        """
        Bulk index documents.
        Returns (success_count, failed_ids).
        """
        ...

    async def get_document(
        self,
        index: str,
        id: str,
    ) -> dict[str, Any] | None:
        """Get document by ID."""
        ...

    async def update_document(
        self,
        index: str,
        id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Partial update a document."""
        ...

    async def delete_document(self, index: str, id: str) -> bool:
        """Delete a document."""
        ...

    async def delete_documents(
        self,
        index: str,
        ids: list[str],
    ) -> int:
        """Bulk delete documents. Returns deleted count."""
        ...

    async def delete_by_filter(
        self,
        index: str,
        filters: list[SearchFilter],
    ) -> int:
        """Delete documents matching filter. Returns deleted count."""
        ...

    # Search
    async def search(
        self,
        index: str,
        query: SearchQuery,
    ) -> SearchResult:
        """Execute search query."""
        ...

    async def multi_search(
        self,
        queries: list[tuple[str, SearchQuery]],
    ) -> list[SearchResult]:
        """Execute multiple searches in one request."""
        ...

    # Synonyms (optional)
    async def set_synonyms(
        self,
        index: str,
        synonyms: dict[str, list[str]],
    ) -> bool:
        """Set synonyms for an index."""
        ...

    # Stats
    async def get_stats(self, index: str) -> dict[str, Any]:
        """Get index statistics (doc count, size, etc.)."""
        ...
