"""
Celery queue backend implementation.

Wraps Celery to provide a consistent async interface.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, TypeVar, Optional
from functools import partial

from celery import Celery
from celery.result import AsyncResult
from celery.exceptions import CeleryError

from src.core.interfaces.queue import TaskStatus, TaskResult, TaskOptions

T = TypeVar("T")


def _celery_state_to_status(state: str) -> TaskStatus:
    """Convert Celery state to TaskStatus."""
    mapping = {
        "PENDING": TaskStatus.PENDING,
        "STARTED": TaskStatus.STARTED,
        "SUCCESS": TaskStatus.SUCCESS,
        "FAILURE": TaskStatus.FAILURE,
        "RETRY": TaskStatus.RETRY,
        "REVOKED": TaskStatus.REVOKED,
    }
    return mapping.get(state, TaskStatus.PENDING)


class CeleryQueueBackend:
    """
    Celery queue backend implementation.

    Provides an async interface to Celery task queue.

    Usage:
        # Initialize with Celery app
        from apps.worker.src.celery_app import app as celery_app
        queue = CeleryQueueBackend(celery_app)

        # Enqueue a task
        task_id = await queue.enqueue(
            "src.tasks.email.send_welcome_email",
            kwargs={"user_id": "123"},
        )

        # Get result
        result = await queue.get_result(task_id, timeout=30)

        # With options
        task_id = await queue.enqueue(
            "src.tasks.webhooks.send_webhook",
            kwargs={"webhook_id": "456", "payload": {...}},
            options=TaskOptions(
                queue="webhooks",
                countdown=60,  # Delay 60 seconds
                max_retries=5,
            ),
        )
    """

    def __init__(
        self,
        app: Optional[Celery] = None,
        broker_url: Optional[str] = None,
        result_backend: Optional[str] = None,
    ):
        """
        Initialize Celery queue backend.

        Args:
            app: Existing Celery application
            broker_url: Broker URL (creates new app if no app provided)
            result_backend: Result backend URL
        """
        if app:
            self._app = app
        else:
            self._app = Celery(
                "saas-api",
                broker=broker_url or "redis://localhost:6379/0",
                backend=result_backend or "redis://localhost:6379/1",
            )

        # Configure default serialization
        self._app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
        )

    @property
    def app(self) -> Celery:
        """Get the Celery application."""
        return self._app

    async def enqueue(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: Optional[dict[str, Any]] = None,
        options: Optional[TaskOptions] = None,
    ) -> str:
        """
        Enqueue a task for execution.

        Returns task_id.
        """
        kwargs = kwargs or {}
        options = options or TaskOptions()

        # Build Celery task options
        celery_options = {
            "queue": options.queue,
            "priority": options.priority,
        }

        if options.countdown:
            celery_options["countdown"] = options.countdown
        if options.eta:
            celery_options["eta"] = options.eta
        if options.expires:
            celery_options["expires"] = options.expires
        if options.timeout:
            celery_options["soft_time_limit"] = options.timeout
        if options.hard_timeout:
            celery_options["time_limit"] = options.hard_timeout

        # Retry configuration
        if not options.retry:
            celery_options["max_retries"] = 0
        else:
            celery_options["max_retries"] = options.max_retries

        # Send task to Celery (use run_in_executor for async compatibility)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                self._app.send_task,
                task_name,
                args=args,
                kwargs=kwargs,
                **celery_options,
            ),
        )

        return result.id

    async def enqueue_many(
        self,
        tasks: list[tuple[str, tuple, Optional[dict[str, Any]]]],
        options: Optional[TaskOptions] = None,
    ) -> list[str]:
        """Enqueue multiple tasks. Returns list of task_ids."""
        task_ids = []
        for task_name, args, kwargs in tasks:
            task_id = await self.enqueue(task_name, args, kwargs, options)
            task_ids.append(task_id)
        return task_ids

    async def get_result(
        self,
        task_id: str,
        timeout: Optional[float] = None,
    ) -> TaskResult:
        """
        Get task result.

        If timeout provided, waits for completion.
        """
        loop = asyncio.get_running_loop()
        result = AsyncResult(task_id, app=self._app)

        try:
            if timeout:
                # Wait for result with timeout
                value = await loop.run_in_executor(
                    None,
                    partial(result.get, timeout=timeout, propagate=False),
                )
            else:
                value = result.result if result.ready() else None

            status = _celery_state_to_status(result.state)

            # Extract error information
            error = None
            traceback = None
            if result.failed():
                error = str(result.result) if result.result else "Unknown error"
                traceback = result.traceback

            return TaskResult(
                task_id=task_id,
                status=status,
                result=value if status == TaskStatus.SUCCESS else None,
                error=error,
                traceback=traceback,
                started_at=None,  # Celery doesn't track this by default
                completed_at=datetime.utcnow() if result.ready() else None,
                retries=result.retries or 0,
            )

        except CeleryError as e:
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILURE,
                error=str(e),
            )

    async def revoke(
        self,
        task_id: str,
        terminate: bool = False,
    ) -> bool:
        """Cancel/revoke a pending or running task."""
        loop = asyncio.get_running_loop()

        try:
            await loop.run_in_executor(
                None,
                partial(
                    self._app.control.revoke,
                    task_id,
                    terminate=terminate,
                    signal="SIGTERM" if terminate else None,
                ),
            )
            return True
        except Exception:
            return False

    async def get_status(self, task_id: str) -> TaskStatus:
        """Get current task status."""
        result = AsyncResult(task_id, app=self._app)
        return _celery_state_to_status(result.state)

    async def schedule(
        self,
        task_name: str,
        schedule: str | timedelta,
        args: tuple = (),
        kwargs: Optional[dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> str:
        """
        Schedule a recurring task.

        Note: This modifies the beat_schedule at runtime.
        For production, use Celery Beat's database scheduler.
        """
        kwargs = kwargs or {}
        schedule_id = name or f"schedule_{task_name}_{id(schedule)}"

        # Convert to Celery schedule format
        if isinstance(schedule, timedelta):
            celery_schedule = schedule.total_seconds()
        else:
            # Assume cron string - needs celery.schedules.crontab
            from celery.schedules import crontab
            parts = schedule.split()
            if len(parts) == 5:
                celery_schedule = crontab(
                    minute=parts[0],
                    hour=parts[1],
                    day_of_month=parts[2],
                    month_of_year=parts[3],
                    day_of_week=parts[4],
                )
            else:
                raise ValueError(f"Invalid cron schedule: {schedule}")

        self._app.conf.beat_schedule[schedule_id] = {
            "task": task_name,
            "schedule": celery_schedule,
            "args": args,
            "kwargs": kwargs,
        }

        return schedule_id

    async def unschedule(self, schedule_id: str) -> bool:
        """Remove a scheduled task."""
        if schedule_id in self._app.conf.beat_schedule:
            del self._app.conf.beat_schedule[schedule_id]
            return True
        return False

    async def list_scheduled(self) -> list[dict[str, Any]]:
        """List all scheduled tasks."""
        schedules = []
        for name, config in self._app.conf.beat_schedule.items():
            schedule = config.get("schedule")
            schedules.append({
                "id": name,
                "task": config.get("task"),
                "schedule": str(schedule),
                "args": config.get("args", ()),
                "kwargs": config.get("kwargs", {}),
                "enabled": True,
            })
        return schedules

    async def purge(self, queue: str = "default") -> int:
        """Purge all pending tasks from queue."""
        loop = asyncio.get_running_loop()

        try:
            count = await loop.run_in_executor(
                None,
                partial(self._app.control.purge, destination=[queue]),
            )
            return count or 0
        except Exception:
            return 0

    async def queue_length(self, queue: str = "default") -> int:
        """Get number of pending tasks in queue."""
        loop = asyncio.get_running_loop()

        try:
            # This requires Redis as the broker
            with self._app.connection_or_acquire() as conn:
                result = await loop.run_in_executor(
                    None,
                    lambda: conn.default_channel.client.llen(queue),
                )
                return result or 0
        except Exception:
            return 0

    def register(
        self,
        name: Optional[str] = None,
        **options,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        Decorator to register a task function.

        This wraps Celery's @app.task decorator.

        Example:
            @queue.register("my_task")
            def my_task(arg1, arg2):
                return arg1 + arg2
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            task_name = name or f"{func.__module__}.{func.__name__}"
            return self._app.task(name=task_name, **options)(func)
        return decorator
