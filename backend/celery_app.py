import os
from celery import Celery
from celery.schedules import crontab

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "podclean",
    broker=redis_url,
    backend=redis_url,
    include=["tasks.pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=1,
)

# Feed poll schedule — defaults to every 30 minutes, configurable via env
_schedule = os.getenv("FEED_POLL_SCHEDULE", "*/30 * * * *")
_parts = _schedule.split()

celery_app.conf.beat_schedule = {
    "poll-feeds": {
        "task": "tasks.pipeline.poll_feeds",
        "schedule": crontab(
            minute=_parts[0],
            hour=_parts[1],
            day_of_month=_parts[2],
            month_of_year=_parts[3],
            day_of_week=_parts[4],
        ),
    }
}
