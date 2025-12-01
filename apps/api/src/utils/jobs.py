"""
Enterprise Job/Queue Utilities.

Supports:
- Fire-and-Forget - best for emails, webhooks, async operations
- Delayed Execution - best for reminders, scheduled operations
- Scheduled/Cron - best for reports, cleanup, recurring tasks
- Chained Jobs - best for multi-step workflows
- Batch Processing - best for bulk operations
- Priority Queues - best for urgent vs normal tasks

Usage:
    # Get job manager
    job_manager = JobManager(queue)

    # Fire-and-Forget (most common)
    task_id = await job_manager.enqueue("send_email", user_id="123")

    # Delayed execution
    task_id = await job_manager.enqueue_delayed(
        "send_reminder",
        delay=timedelta(hours=24),
        user_id="123",
    )

    # Scheduled/Cron job
    schedule_id = await job_manager.schedule(
        "daily_report",
        cron="0 9 * * *",  # 9 AM daily
    )

    # High priority
    task_id = await job_manager.enqueue(
        "urgent_notification",
        priority=JobPriority.CRITICAL,
        user_id="123",
    )

    # Batch processing
    task_ids = await job_manager.enqueue_batch(
        "process_item",
        items=[{"id": "1"}, {"id": "2"}, {"id": "3"}],
    )
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from enum import IntEnum, Enum
from typing import (
    TypeVar,
    Any,
    Optional,
    Union,
    Sequence,
    Callable,
    Awaitable,
)
from dataclasses import dataclass, field

from pydantic import BaseModel
from fastapi import Depends

from src.core.interfaces.queue import QueueBackend, TaskStatus, TaskResult, TaskOptions
from src.core.plugins.registry import queue_backends

T = TypeVar("T")


# ============================================================
# JOB PRIORITY LEVELS
# ============================================================

class JobPriority(IntEnum):
    """Job priority levels (higher = more urgent)."""
    LOW = 0       # Background, can wait
    NORMAL = 5    # Standard priority
    HIGH = 8      # Should run soon
    CRITICAL = 10 # Must run immediately


# ============================================================
# JOB PATTERNS ENUM
# ============================================================

class JobPattern(str, Enum):
    """Common job patterns."""
    FIRE_AND_FORGET = "fire_and_forget"
    DELAYED = "delayed"
    SCHEDULED = "scheduled"
    CHAINED = "chained"
    BATCH = "batch"


# ============================================================
# JOB SCHEMAS (for API responses)
# ============================================================

class JobStatus(BaseModel):
    """Job status response."""
    id: str
    task: str
    status: str
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0


class ScheduledJobInfo(BaseModel):
    """Scheduled job info."""
    id: str
    task: str
    schedule: str
    name: Optional[str] = None
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class JobBatchResult(BaseModel):
    """Batch job result."""
    total: int
    enqueued: int
    task_ids: list[str]


# ============================================================
# JOB MANAGER
# ============================================================

class JobManager:
    """
    Unified job manager supporting multiple job patterns.

    Similar to Paginator, provides a single interface with multiple
    methods for different use cases.

    Usage:
        job_manager = JobManager(queue)

        # Simple async task
        await job_manager.enqueue("send_email", user_id="123")

        # Delayed task
        await job_manager.enqueue_delayed(
            "send_reminder",
            delay=timedelta(hours=1),
        )

        # Scheduled task
        await job_manager.schedule(
            "cleanup_expired",
            cron="0 * * * *",  # Every hour
        )
    """

    def __init__(self, queue: QueueBackend):
        """Initialize with a queue backend."""
        self.queue = queue

    # --- Fire-and-Forget Pattern ---

    async def enqueue(
        self,
        task: str,
        *args,
        priority: JobPriority = JobPriority.NORMAL,
        queue: str = "default",
        **kwargs,
    ) -> str:
        """
        Enqueue a task for immediate async execution.

        Best for:
        - Sending emails/notifications
        - Webhook deliveries
        - Non-blocking async operations

        Args:
            task: Task name (e.g., "src.tasks.email.send_welcome")
            *args: Positional arguments for the task
            priority: Job priority level
            queue: Queue name for routing
            **kwargs: Keyword arguments for the task

        Returns:
            Task ID for tracking

        Example:
            task_id = await job_manager.enqueue(
                "send_email",
                to="user@example.com",
                subject="Welcome!",
            )
        """
        options = TaskOptions(
            queue=queue,
            priority=priority,
        )

        return await self.queue.enqueue(
            task,
            args=args,
            kwargs=kwargs if kwargs else None,
            options=options,
        )

    # --- Delayed Execution Pattern ---

    async def enqueue_delayed(
        self,
        task: str,
        delay: Union[int, timedelta],
        *args,
        priority: JobPriority = JobPriority.NORMAL,
        queue: str = "default",
        **kwargs,
    ) -> str:
        """
        Enqueue a task to execute after a delay.

        Best for:
        - Reminders and follow-ups
        - Rate limiting
        - Debounced operations

        Args:
            task: Task name
            delay: Delay in seconds or timedelta
            *args: Positional arguments
            priority: Job priority
            queue: Queue name
            **kwargs: Keyword arguments

        Returns:
            Task ID

        Example:
            # Send reminder in 24 hours
            task_id = await job_manager.enqueue_delayed(
                "send_reminder",
                delay=timedelta(hours=24),
                user_id="123",
            )
        """
        countdown = int(delay.total_seconds()) if isinstance(delay, timedelta) else delay

        options = TaskOptions(
            queue=queue,
            priority=priority,
            countdown=countdown,
        )

        return await self.queue.enqueue(
            task,
            args=args,
            kwargs=kwargs if kwargs else None,
            options=options,
        )

    # --- Scheduled Execution Pattern ---

    async def enqueue_at(
        self,
        task: str,
        execute_at: datetime,
        *args,
        priority: JobPriority = JobPriority.NORMAL,
        queue: str = "default",
        **kwargs,
    ) -> str:
        """
        Enqueue a task to execute at a specific time.

        Best for:
        - Scheduled reports
        - Timed announcements
        - Calendar-based operations

        Args:
            task: Task name
            execute_at: Exact datetime to execute
            *args: Positional arguments
            priority: Job priority
            queue: Queue name
            **kwargs: Keyword arguments

        Returns:
            Task ID

        Example:
            # Send report at 9 AM tomorrow
            task_id = await job_manager.enqueue_at(
                "send_daily_report",
                execute_at=datetime(2024, 1, 2, 9, 0, 0),
                report_type="sales",
            )
        """
        options = TaskOptions(
            queue=queue,
            priority=priority,
            eta=execute_at,
        )

        return await self.queue.enqueue(
            task,
            args=args,
            kwargs=kwargs if kwargs else None,
            options=options,
        )

    # --- Cron Scheduling Pattern ---

    async def schedule(
        self,
        task: str,
        cron: str,
        *args,
        name: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Schedule a recurring task using cron expression.

        Best for:
        - Daily/weekly reports
        - Cleanup jobs
        - Periodic syncs

        Args:
            task: Task name
            cron: Cron expression (e.g., "0 9 * * *" for 9 AM daily)
            *args: Positional arguments
            name: Optional schedule name
            **kwargs: Keyword arguments

        Returns:
            Schedule ID

        Cron format: minute hour day_of_month month day_of_week
        Examples:
            "0 9 * * *"     - 9 AM daily
            "0 0 * * 0"     - Midnight every Sunday
            "*/15 * * * *"  - Every 15 minutes
            "0 9 1 * *"     - 9 AM on 1st of each month

        Example:
            schedule_id = await job_manager.schedule(
                "generate_report",
                cron="0 9 * * 1",  # 9 AM every Monday
                name="weekly-report",
            )
        """
        return await self.queue.schedule(
            task,
            schedule=cron,
            args=args,
            kwargs=kwargs if kwargs else None,
            name=name,
        )

    async def schedule_interval(
        self,
        task: str,
        interval: timedelta,
        *args,
        name: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Schedule a recurring task at fixed intervals.

        Best for:
        - Health checks
        - Cache warmup
        - Polling operations

        Args:
            task: Task name
            interval: Time between executions
            *args: Positional arguments
            name: Optional schedule name
            **kwargs: Keyword arguments

        Returns:
            Schedule ID

        Example:
            schedule_id = await job_manager.schedule_interval(
                "health_check",
                interval=timedelta(minutes=5),
                name="api-health",
            )
        """
        return await self.queue.schedule(
            task,
            schedule=interval,
            args=args,
            kwargs=kwargs if kwargs else None,
            name=name,
        )

    async def unschedule(self, schedule_id: str) -> bool:
        """Remove a scheduled task."""
        return await self.queue.unschedule(schedule_id)

    async def list_scheduled(self) -> list[ScheduledJobInfo]:
        """List all scheduled tasks."""
        schedules = await self.queue.list_scheduled()
        return [
            ScheduledJobInfo(
                id=s.get("id", ""),
                task=s.get("task", ""),
                schedule=s.get("schedule", ""),
                name=s.get("name"),
                enabled=s.get("enabled", True),
                last_run=s.get("last_run"),
                next_run=s.get("next_run"),
            )
            for s in schedules
        ]

    # --- Chained Jobs Pattern ---

    async def chain(
        self,
        tasks: Sequence[tuple[str, tuple, Optional[dict[str, Any]]]],
        queue: str = "default",
    ) -> str:
        """
        Chain multiple tasks to execute sequentially.

        Each task runs after the previous one completes.

        Best for:
        - Multi-step workflows
        - Data pipelines
        - Saga patterns

        Args:
            tasks: List of (task_name, args, kwargs) tuples
            queue: Queue for all tasks

        Returns:
            First task ID (chain head)

        Example:
            task_id = await job_manager.chain([
                ("validate_order", (), {"order_id": "123"}),
                ("process_payment", (), {"order_id": "123"}),
                ("send_confirmation", (), {"order_id": "123"}),
            ])
        """
        # For backends that support chaining natively, use that
        # Otherwise, we return the first task ID
        task_ids = await self.queue.enqueue_many(
            list(tasks),
            options=TaskOptions(queue=queue),
        )
        return task_ids[0] if task_ids else ""

    # --- Batch Processing Pattern ---

    async def enqueue_batch(
        self,
        task: str,
        items: Sequence[dict[str, Any]],
        batch_size: int = 100,
        priority: JobPriority = JobPriority.NORMAL,
        queue: str = "default",
    ) -> JobBatchResult:
        """
        Enqueue a task for each item in a batch.

        Best for:
        - Bulk email sending
        - Mass data processing
        - Import/export operations

        Args:
            task: Task name to run for each item
            items: List of kwargs dicts for each task
            batch_size: Max items per batch (for chunking)
            priority: Job priority
            queue: Queue name

        Returns:
            BatchResult with task IDs

        Example:
            result = await job_manager.enqueue_batch(
                "process_user",
                items=[
                    {"user_id": "1"},
                    {"user_id": "2"},
                    {"user_id": "3"},
                ],
            )
            print(f"Enqueued {result.enqueued} jobs")
        """
        tasks = [(task, (), item) for item in items]
        options = TaskOptions(queue=queue, priority=priority)

        task_ids = await self.queue.enqueue_many(tasks, options=options)

        return JobBatchResult(
            total=len(items),
            enqueued=len(task_ids),
            task_ids=task_ids,
        )

    # --- Job Status & Control ---

    async def get_status(self, task_id: str) -> JobStatus:
        """
        Get current status of a job.

        Example:
            status = await job_manager.get_status(task_id)
            if status.status == "success":
                print(f"Result: {status.result}")
        """
        result = await self.queue.get_result(task_id)

        return JobStatus(
            id=task_id,
            task="",  # Not always available
            status=result.status.value,
            started_at=result.started_at,
            completed_at=result.completed_at,
            result=result.result,
            error=result.error,
            retries=result.retries,
        )

    async def wait_for(
        self,
        task_id: str,
        timeout: float = 30.0,
    ) -> TaskResult:
        """
        Wait for a job to complete.

        Example:
            result = await job_manager.wait_for(task_id, timeout=60)
            if result.status == TaskStatus.SUCCESS:
                print(f"Done: {result.result}")
        """
        return await self.queue.get_result(task_id, timeout=timeout)

    async def cancel(self, task_id: str, terminate: bool = False) -> bool:
        """
        Cancel a pending or running job.

        Args:
            task_id: Job to cancel
            terminate: Force terminate if running

        Example:
            cancelled = await job_manager.cancel(task_id)
        """
        return await self.queue.revoke(task_id, terminate=terminate)

    # --- Queue Management ---

    async def queue_length(self, queue: str = "default") -> int:
        """Get number of pending jobs in queue."""
        return await self.queue.queue_length(queue)

    async def purge_queue(self, queue: str = "default") -> int:
        """Purge all pending jobs from a queue."""
        return await self.queue.purge(queue)


# ============================================================
# FASTAPI DEPENDENCIES
# ============================================================

async def get_queue() -> QueueBackend:
    """
    FastAPI dependency to get the configured queue backend.

    Usage:
        @router.post("/jobs")
        async def create_job(queue: QueueBackend = Depends(get_queue)):
            task_id = await queue.enqueue("my_task")
            ...
    """
    try:
        return await queue_backends.get_async("celery")
    except Exception:
        # Fallback to memory queue for development/testing
        return await queue_backends.get_async("memory")


async def get_job_manager() -> JobManager:
    """
    FastAPI dependency to get the job manager.

    Usage:
        @router.post("/send-email")
        async def send_email(
            data: EmailRequest,
            jobs: JobManager = Depends(get_job_manager),
        ):
            task_id = await jobs.enqueue(
                "send_email",
                to=data.to,
                subject=data.subject,
            )
            return {"task_id": task_id}
    """
    queue = await get_queue()
    return JobManager(queue)


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def enqueue(
    task: str,
    *args,
    priority: JobPriority = JobPriority.NORMAL,
    queue: str = "default",
    **kwargs,
) -> str:
    """
    Quick enqueue without creating a JobManager.

    Example:
        from src.utils.jobs import enqueue
        task_id = await enqueue("send_email", to="user@example.com")
    """
    queue_backend = await queue_backends.get_async("celery")
    manager = JobManager(queue_backend)
    return await manager.enqueue(task, *args, priority=priority, queue=queue, **kwargs)


async def enqueue_delayed(
    task: str,
    delay: Union[int, timedelta],
    *args,
    **kwargs,
) -> str:
    """
    Quick delayed enqueue.

    Example:
        from src.utils.jobs import enqueue_delayed
        task_id = await enqueue_delayed("send_reminder", timedelta(hours=1))
    """
    queue_backend = await queue_backends.get_async("celery")
    manager = JobManager(queue_backend)
    return await manager.enqueue_delayed(task, delay, *args, **kwargs)
