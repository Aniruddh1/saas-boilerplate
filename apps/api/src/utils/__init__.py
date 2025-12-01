"""Utility functions."""

from src.utils.caching import (
    # Patterns
    CachePattern,
    # Decorators
    cache_aside,
    write_through,
    stampede_protect,
    memoize,
    cached,  # Alias for cache_aside
    # Key utilities
    build_cache_key,
    hash_args,
    make_key,
    # Invalidation
    invalidate_keys,
    invalidate_pattern,
    invalidate_tags,
    tag_cache_key,
    # FastAPI dependencies
    get_cache,
    cached_response,
    # Stats
    CacheStats,
    get_cache_stats,
)

from src.utils.jobs import (
    # Priority
    JobPriority,
    JobPattern,
    # Schemas
    JobStatus,
    ScheduledJobInfo,
    JobBatchResult,
    # Manager
    JobManager,
    # FastAPI dependencies
    get_queue,
    get_job_manager,
    # Convenience functions
    enqueue,
    enqueue_delayed,
)

from src.utils.notifications import (
    # Schemas
    NotificationResponse,
    NotificationCreate,
    BroadcastRequest,
    NotifyResult,
    BroadcastResult,
    # Manager
    Notifier,
    # Helper
    create_notification,
    # FastAPI dependencies
    get_notifier,
    get_database_channel,
)

from src.utils.pagination import (
    # Pagination modes
    PaginationMode,
    # Offset pagination
    OffsetParams,
    OffsetPage,
    get_offset_params,
    # Cursor pagination
    CursorParams,
    CursorPage,
    get_cursor_params,
    encode_cursor,
    decode_cursor,
    # Unified paginator
    Paginator,
    # Streaming/Export
    ExportFormat,
    stream_query,
    create_csv_streaming_response,
    create_jsonl_streaming_response,
    # Legacy aliases
    PaginationParams,
    PaginatedResponse,
    Page,
    get_pagination,
)

__all__ = [
    # Caching patterns
    "CachePattern",
    "cache_aside",
    "write_through",
    "stampede_protect",
    "memoize",
    "cached",
    # Cache key utilities
    "build_cache_key",
    "hash_args",
    "make_key",
    # Cache invalidation
    "invalidate_keys",
    "invalidate_pattern",
    "invalidate_tags",
    "tag_cache_key",
    # Cache dependencies
    "get_cache",
    "cached_response",
    # Cache stats
    "CacheStats",
    "get_cache_stats",
    # Job priority
    "JobPriority",
    "JobPattern",
    # Job schemas
    "JobStatus",
    "ScheduledJobInfo",
    "JobBatchResult",
    # Job manager
    "JobManager",
    # Job dependencies
    "get_queue",
    "get_job_manager",
    # Job convenience functions
    "enqueue",
    "enqueue_delayed",
    # Notification schemas
    "NotificationResponse",
    "NotificationCreate",
    "BroadcastRequest",
    "NotifyResult",
    "BroadcastResult",
    # Notification manager
    "Notifier",
    # Notification helper
    "create_notification",
    # Notification dependencies
    "get_notifier",
    "get_database_channel",
    # Pagination modes
    "PaginationMode",
    # Offset pagination
    "OffsetParams",
    "OffsetPage",
    "get_offset_params",
    # Cursor pagination
    "CursorParams",
    "CursorPage",
    "get_cursor_params",
    "encode_cursor",
    "decode_cursor",
    # Unified paginator
    "Paginator",
    # Streaming/Export
    "ExportFormat",
    "stream_query",
    "create_csv_streaming_response",
    "create_jsonl_streaming_response",
    # Legacy aliases
    "PaginationParams",
    "PaginatedResponse",
    "Page",
    "get_pagination",
]
