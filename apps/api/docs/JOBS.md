# Background Jobs System

Enterprise-grade job/queue utilities with progressive complexity, supporting fire-and-forget, delayed, scheduled, chained, and batch job patterns.

## Overview

| Level | Complexity | Use Case |
|-------|------------|----------|
| 1 | Simple | Fire-and-forget async tasks |
| 2 | Delayed | Execute after a delay |
| 3 | Scheduled | Cron-based recurring jobs |
| 4 | Chained | Multi-step workflows |
| 5 | Batch | Bulk operations |

## Quick Start

### Level 1: Fire-and-Forget

Best for async operations that don't need immediate results.

```python
from src.utils.jobs import get_job_manager, JobManager
from fastapi import Depends

@router.post("/signup")
async def signup(
    data: SignupRequest,
    jobs: JobManager = Depends(get_job_manager),
):
    user = await create_user(data)

    # Send welcome email asynchronously
    await jobs.enqueue("send_welcome_email", user_id=str(user.id))

    return {"user_id": user.id}
```

### Level 2: Delayed Execution

Best for reminders, follow-ups, and rate limiting.

```python
from datetime import timedelta

@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: str,
    jobs: JobManager = Depends(get_job_manager),
):
    order = await confirm(order_id)

    # Send review request in 7 days
    await jobs.enqueue_delayed(
        "request_review",
        delay=timedelta(days=7),
        order_id=order_id,
    )

    return order
```

### Level 3: Scheduled/Cron Jobs

Best for recurring tasks like reports and cleanup.

```python
# In app startup
async def setup_scheduled_jobs():
    jobs = await get_job_manager()

    # Daily report at 9 AM
    await jobs.schedule(
        "generate_daily_report",
        cron="0 9 * * *",
        name="daily-report",
    )

    # Cleanup expired sessions every hour
    await jobs.schedule(
        "cleanup_sessions",
        cron="0 * * * *",
        name="session-cleanup",
    )

    # Health check every 5 minutes
    await jobs.schedule_interval(
        "health_check",
        interval=timedelta(minutes=5),
        name="health-ping",
    )
```

### Level 4: Chained Jobs (Workflows)

Best for multi-step processes that must run in sequence.

```python
@router.post("/orders")
async def create_order(
    data: OrderRequest,
    jobs: JobManager = Depends(get_job_manager),
):
    order = await save_order(data)

    # Chain: validate -> process payment -> send confirmation
    await jobs.chain([
        ("validate_order", (), {"order_id": str(order.id)}),
        ("process_payment", (), {"order_id": str(order.id)}),
        ("send_confirmation", (), {"order_id": str(order.id)}),
    ])

    return order
```

### Level 5: Batch Processing

Best for bulk operations on many items.

```python
@router.post("/admin/send-newsletter")
async def send_newsletter(
    data: NewsletterRequest,
    jobs: JobManager = Depends(get_job_manager),
):
    subscribers = await get_subscribers()

    # Enqueue job for each subscriber
    result = await jobs.enqueue_batch(
        "send_newsletter_email",
        items=[{"user_id": str(s.id), "content": data.content} for s in subscribers],
        batch_size=100,
    )

    return {
        "total": result.total,
        "enqueued": result.enqueued,
    }
```

## Architecture

```
src/utils/jobs.py                    # JobManager and utilities
src/core/interfaces/queue.py         # QueueBackend protocol
src/implementations/queue/
├── memory.py                        # In-memory backend (dev)
└── celery.py                        # Celery backend (production)
```

## Configuration

```env
# Queue backend: celery (production) or memory (dev)
QUEUE_BACKEND=celery

# Celery broker
CELERY_BROKER_URL=redis://localhost:6379/1

# Celery result backend
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## Job Priority Levels

```python
from src.utils.jobs import JobPriority

# Background tasks that can wait
await jobs.enqueue("cleanup", priority=JobPriority.LOW)

# Standard priority (default)
await jobs.enqueue("send_email", priority=JobPriority.NORMAL)

# Should run soon
await jobs.enqueue("process_payment", priority=JobPriority.HIGH)

# Must run immediately
await jobs.enqueue("fraud_alert", priority=JobPriority.CRITICAL)
```

| Priority | Value | Use Case |
|----------|-------|----------|
| `LOW` | 0 | Background cleanup, analytics |
| `NORMAL` | 5 | Standard async operations |
| `HIGH` | 8 | Time-sensitive tasks |
| `CRITICAL` | 10 | Urgent alerts, fraud detection |

## Cron Expression Format

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, 0=Sunday)
│ │ │ │ │
* * * * *
```

Common patterns:
```
"0 9 * * *"     - 9:00 AM daily
"0 0 * * 0"     - Midnight every Sunday
"*/15 * * * *"  - Every 15 minutes
"0 9 1 * *"     - 9:00 AM on 1st of each month
"0 */2 * * *"   - Every 2 hours
"30 4 * * 1-5"  - 4:30 AM weekdays
```

## Job Status & Control

### Get Job Status

```python
status = await jobs.get_status(task_id)

if status.status == "success":
    print(f"Result: {status.result}")
elif status.status == "failed":
    print(f"Error: {status.error}")
```

### Wait for Completion

```python
result = await jobs.wait_for(task_id, timeout=60)

if result.status == TaskStatus.SUCCESS:
    return result.result
else:
    raise Exception(result.error)
```

### Cancel Job

```python
# Cancel pending job
cancelled = await jobs.cancel(task_id)

# Force terminate running job
cancelled = await jobs.cancel(task_id, terminate=True)
```

## Queue Management

```python
# Get queue length
pending = await jobs.queue_length("default")

# Purge all pending jobs
purged = await jobs.purge_queue("default")

# List scheduled jobs
schedules = await jobs.list_scheduled()
for s in schedules:
    print(f"{s.name}: {s.schedule} (next: {s.next_run})")

# Unschedule a job
await jobs.unschedule(schedule_id)
```

## FastAPI Dependencies

```python
from src.utils.jobs import get_job_manager, get_queue, JobManager
from src.core.interfaces.queue import QueueBackend

# High-level JobManager (recommended)
@router.post("/tasks")
async def create_task(jobs: JobManager = Depends(get_job_manager)):
    task_id = await jobs.enqueue("my_task", arg1="value")
    return {"task_id": task_id}

# Low-level queue access
@router.get("/queue-stats")
async def queue_stats(queue: QueueBackend = Depends(get_queue)):
    length = await queue.queue_length("default")
    return {"pending": length}
```

## Convenience Functions

For quick one-off jobs without creating a JobManager:

```python
from src.utils.jobs import enqueue, enqueue_delayed

# Fire and forget
task_id = await enqueue("send_email", to="user@example.com")

# Delayed execution
task_id = await enqueue_delayed(
    "send_reminder",
    timedelta(hours=1),
    user_id="123",
)
```

## Writing Task Handlers

Define your tasks in a tasks module:

```python
# src/tasks/email.py
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def send_email(self, to: str, subject: str, body: str):
    """Send an email."""
    try:
        # Send email logic
        mailer.send(to=to, subject=subject, body=body)
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

@shared_task
def send_welcome_email(user_id: str):
    """Send welcome email to new user."""
    user = get_user_sync(user_id)
    send_email(
        to=user.email,
        subject="Welcome!",
        body=f"Hi {user.name}, welcome to our platform!",
    )
```

## Pattern Selection Guide

| Pattern | Use When | Example |
|---------|----------|---------|
| Fire-and-forget | Async ops, don't need result | Emails, webhooks |
| Delayed | Need to wait before execution | Reminders, follow-ups |
| Scheduled (cron) | Recurring at specific times | Reports, cleanup |
| Scheduled (interval) | Recurring at fixed intervals | Health checks |
| Chained | Sequential multi-step workflow | Order processing |
| Batch | Same task for many items | Mass emails, imports |

## Best Practices

1. **Keep tasks idempotent** - Tasks may be retried, so running twice should be safe
2. **Set appropriate timeouts** - Don't let tasks run forever
3. **Use priority wisely** - Most tasks should be NORMAL
4. **Monitor queue lengths** - Alert if queues back up
5. **Log task execution** - For debugging and auditing
6. **Handle failures gracefully** - Implement retries with backoff
7. **Use separate queues** - Route critical tasks to dedicated queues

## Testing

Use memory backend for tests:

```python
import pytest
from src.utils.jobs import JobManager
from src.implementations.queue.memory import MemoryQueueBackend

@pytest.fixture
def job_manager():
    backend = MemoryQueueBackend()
    return JobManager(backend)

async def test_enqueue_job(job_manager):
    task_id = await job_manager.enqueue("test_task", arg="value")
    assert task_id is not None

    # In memory backend, tasks execute immediately
    status = await job_manager.get_status(task_id)
    assert status.status in ["pending", "success"]
```
