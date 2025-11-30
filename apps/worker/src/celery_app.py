"""
Celery application configuration.
"""

from celery import Celery
from src.config import settings

app = Celery(
    "saas-worker",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=[
        "src.tasks.email",
        "src.tasks.webhooks",
        "src.tasks.scheduled",
    ],
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "src.tasks.email.*": {"queue": "email"},
        "src.tasks.webhooks.*": {"queue": "webhooks"},
        "src.tasks.scheduled.*": {"queue": "scheduled"},
    },

    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,

    # Result backend settings
    result_expires=3600,

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Beat schedule (periodic tasks)
    beat_schedule={
        "cleanup-expired-tokens": {
            "task": "src.tasks.scheduled.cleanup_expired_tokens",
            "schedule": 3600.0,  # Every hour
        },
        "send-digest-emails": {
            "task": "src.tasks.scheduled.send_digest_emails",
            "schedule": 86400.0,  # Daily
        },
    },
)


if __name__ == "__main__":
    app.start()
