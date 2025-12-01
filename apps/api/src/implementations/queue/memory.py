"""
In-memory queue backend for testing and development.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, TypeVar
from dataclasses import dataclass, field
from collections import defaultdict

from src.core.interfaces.queue import TaskStatus, TaskResult, TaskOptions

T = TypeVar("T")


@dataclass
class QueuedTask:
    """Internal representation of a queued task."""
    task_id: str
    task_name: str
    args: tuple
    kwargs: dict[str, Any]
    options: TaskOptions
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    traceback: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retries: int = 0


@dataclass
class ScheduledTask:
    """Internal representation of a scheduled task."""
    schedule_id: str
    task_name: str
    schedule: str | timedelta
    args: tuple
    kwargs: dict[str, Any]
    name: str | None
    last_run: datetime | None = None
    next_run: datetime | None = None
    enabled: bool = True


class MemoryQueueBackend:
    """
    In-memory queue backend for testing and development.

    All tasks are executed immediately in the same process.
    Useful for unit tests and local development without Redis/RabbitMQ.

    Usage:
        queue = MemoryQueueBackend()

        # Register a task
        @queue.register("send_email")
        async def send_email(to: str, subject: str):
            print(f"Sending email to {to}: {subject}")

        # Enqueue (executes immediately in memory mode)
        task_id = await queue.enqueue("send_email", kwargs={"to": "user@example.com", "subject": "Hello"})

        # Get result
        result = await queue.get_result(task_id)
    """

    def __init__(
        self,
        execute_immediately: bool = True,
        store_results: bool = True,
    ):
        """
        Initialize the memory queue.

        Args:
            execute_immediately: Execute tasks immediately when enqueued
            store_results: Store task results (disable for memory efficiency in tests)
        """
        self.execute_immediately = execute_immediately
        self.store_results = store_results

        # Storage
        self._tasks: dict[str, QueuedTask] = {}
        self._scheduled: dict[str, ScheduledTask] = {}
        self._queues: dict[str, list[str]] = defaultdict(list)
        self._handlers: dict[str, Callable] = {}

    def register(
        self,
        name: str | None = None,
        **options,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        Decorator to register a task function.

        Example:
            @queue.register("my_task")
            async def my_task(arg1, arg2):
                return arg1 + arg2
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            task_name = name or f"{func.__module__}.{func.__name__}"
            self._handlers[task_name] = func
            return func
        return decorator

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
        kwargs = kwargs or {}
        options = options or TaskOptions()

        task_id = str(uuid.uuid4())
        task = QueuedTask(
            task_id=task_id,
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            options=options,
        )

        self._tasks[task_id] = task
        self._queues[options.queue].append(task_id)

        # Execute immediately if configured
        if self.execute_immediately:
            await self._execute_task(task)

        return task_id

    async def enqueue_many(
        self,
        tasks: list[tuple[str, tuple, dict[str, Any] | None]],
        options: TaskOptions | None = None,
    ) -> list[str]:
        """Enqueue multiple tasks. Returns list of task_ids."""
        task_ids = []
        for task_name, args, kwargs in tasks:
            task_id = await self.enqueue(task_name, args, kwargs, options)
            task_ids.append(task_id)
        return task_ids

    async def _execute_task(self, task: QueuedTask) -> None:
        """Execute a task immediately."""
        handler = self._handlers.get(task.task_name)

        if not handler:
            task.status = TaskStatus.FAILURE
            task.error = f"No handler registered for task: {task.task_name}"
            task.completed_at = datetime.utcnow()
            return

        task.status = TaskStatus.STARTED
        task.started_at = datetime.utcnow()

        try:
            # Check if handler is async
            if asyncio.iscoroutinefunction(handler):
                result = await handler(*task.args, **task.kwargs)
            else:
                result = handler(*task.args, **task.kwargs)

            task.status = TaskStatus.SUCCESS
            task.result = result
        except Exception as e:
            task.status = TaskStatus.FAILURE
            task.error = str(e)
            import traceback
            task.traceback = traceback.format_exc()
        finally:
            task.completed_at = datetime.utcnow()

    async def get_result(
        self,
        task_id: str,
        timeout: float | None = None,
    ) -> TaskResult:
        """
        Get task result.

        If timeout provided, waits for completion.
        """
        task = self._tasks.get(task_id)

        if not task:
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.PENDING,
                error="Task not found",
            )

        # Wait for completion if timeout specified
        if timeout and task.status in (TaskStatus.PENDING, TaskStatus.STARTED):
            start = datetime.utcnow()
            while (datetime.utcnow() - start).total_seconds() < timeout:
                if task.status not in (TaskStatus.PENDING, TaskStatus.STARTED):
                    break
                await asyncio.sleep(0.1)

        return TaskResult(
            task_id=task.task_id,
            status=task.status,
            result=task.result,
            error=task.error,
            traceback=task.traceback,
            started_at=task.started_at,
            completed_at=task.completed_at,
            retries=task.retries,
        )

    async def revoke(
        self,
        task_id: str,
        terminate: bool = False,
    ) -> bool:
        """Cancel/revoke a pending or running task."""
        task = self._tasks.get(task_id)

        if not task:
            return False

        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.REVOKED
            return True

        return False

    async def get_status(self, task_id: str) -> TaskStatus:
        """Get current task status."""
        task = self._tasks.get(task_id)
        return task.status if task else TaskStatus.PENDING

    async def schedule(
        self,
        task_name: str,
        schedule: str | timedelta,
        args: tuple = (),
        kwargs: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> str:
        """
        Schedule a recurring task.

        Note: In memory mode, scheduling is stored but not executed.
        Use a real backend (Celery) for actual scheduled execution.
        """
        kwargs = kwargs or {}
        schedule_id = str(uuid.uuid4())

        scheduled = ScheduledTask(
            schedule_id=schedule_id,
            task_name=task_name,
            schedule=schedule,
            args=args,
            kwargs=kwargs,
            name=name,
        )

        self._scheduled[schedule_id] = scheduled
        return schedule_id

    async def unschedule(self, schedule_id: str) -> bool:
        """Remove a scheduled task."""
        if schedule_id in self._scheduled:
            del self._scheduled[schedule_id]
            return True
        return False

    async def list_scheduled(self) -> list[dict[str, Any]]:
        """List all scheduled tasks."""
        return [
            {
                "id": s.schedule_id,
                "task": s.task_name,
                "schedule": str(s.schedule),
                "name": s.name,
                "enabled": s.enabled,
                "last_run": s.last_run.isoformat() if s.last_run else None,
                "next_run": s.next_run.isoformat() if s.next_run else None,
            }
            for s in self._scheduled.values()
        ]

    async def purge(self, queue: str = "default") -> int:
        """Purge all pending tasks from queue."""
        task_ids = self._queues.get(queue, [])
        count = 0

        for task_id in list(task_ids):
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.REVOKED
                count += 1

        return count

    async def queue_length(self, queue: str = "default") -> int:
        """Get number of pending tasks in queue."""
        task_ids = self._queues.get(queue, [])
        return sum(
            1 for tid in task_ids
            if self._tasks.get(tid) and self._tasks[tid].status == TaskStatus.PENDING
        )

    # Test helpers

    def clear(self) -> None:
        """Clear all tasks and scheduled items (for testing)."""
        self._tasks.clear()
        self._scheduled.clear()
        self._queues.clear()

    def get_all_tasks(self) -> list[QueuedTask]:
        """Get all tasks (for testing)."""
        return list(self._tasks.values())
