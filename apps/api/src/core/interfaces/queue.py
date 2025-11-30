"""
Queue/Task backend protocol.
Implementations: CeleryQueue, RQQueue, DramatiqQueue, InMemoryQueue
"""
from __future__ import annotations

from typing import Protocol, Any, Callable, TypeVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


@dataclass
class TaskResult:
    """Result of a queued task."""
    task_id: str
    status: TaskStatus
    result: Any | None = None
    error: str | None = None
    traceback: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retries: int = 0


@dataclass
class TaskOptions:
    """Options for task execution."""
    queue: str = "default"
    priority: int = 0  # Higher = more priority
    countdown: int | None = None  # Delay in seconds
    eta: datetime | None = None  # Exact execution time
    expires: int | datetime | None = None  # Task expiry
    retry: bool = True
    max_retries: int = 3
    retry_backoff: bool = True  # Exponential backoff
    retry_backoff_max: int = 600  # Max backoff in seconds
    timeout: int | None = None  # Soft time limit
    hard_timeout: int | None = None  # Hard time limit


T = TypeVar("T")


class QueueBackend(Protocol):
    """
    Protocol for task queue backends.

    Example implementations:
    - CeleryQueueBackend: Celery with Redis/RabbitMQ broker
    - RQQueueBackend: Redis Queue
    - DramatiqQueueBackend: Dramatiq
    - InMemoryQueueBackend: For testing
    """

    async def enqueue(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: dict[str, Any] | None = None,
        options: TaskOptions | None = None,
    ) -> str:
        """
        Enqueue a task for execution.
        Returns task_id.
        """
        ...

    async def enqueue_many(
        self,
        tasks: list[tuple[str, tuple, dict[str, Any] | None]],
        options: TaskOptions | None = None,
    ) -> list[str]:
        """Enqueue multiple tasks. Returns list of task_ids."""
        ...

    async def get_result(
        self,
        task_id: str,
        timeout: float | None = None,
    ) -> TaskResult:
        """
        Get task result.
        If timeout provided, waits for completion.
        """
        ...

    async def revoke(
        self,
        task_id: str,
        terminate: bool = False,
    ) -> bool:
        """Cancel/revoke a pending or running task."""
        ...

    async def get_status(self, task_id: str) -> TaskStatus:
        """Get current task status."""
        ...

    # Scheduling
    async def schedule(
        self,
        task_name: str,
        schedule: str | timedelta,  # Cron string or interval
        args: tuple = (),
        kwargs: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> str:
        """
        Schedule a recurring task.
        schedule: Cron string ("0 * * * *") or timedelta for interval.
        Returns schedule_id.
        """
        ...

    async def unschedule(self, schedule_id: str) -> bool:
        """Remove a scheduled task."""
        ...

    async def list_scheduled(self) -> list[dict[str, Any]]:
        """List all scheduled tasks."""
        ...

    # Queue management
    async def purge(self, queue: str = "default") -> int:
        """Purge all pending tasks from queue. Returns count."""
        ...

    async def queue_length(self, queue: str = "default") -> int:
        """Get number of pending tasks in queue."""
        ...

    # Task registration (for type safety)
    def register(
        self,
        name: str | None = None,
        **options,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to register a task function."""
        ...
