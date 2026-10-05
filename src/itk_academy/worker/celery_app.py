from celery import Celery
from celery.schedules import crontab

from itk_academy.config import get_settings

settings = get_settings()

celery_app = Celery(
    "itk_academy",
    broker=settings.celery_broker_url,
    backend=None,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    timezone="UTC",
    enable_utc=True,
    task_track_started=False,
    broker_connection_retry_on_startup=True,
    imports=("itk_academy.worker.tasks",),
    beat_schedule={
        "sync-events-daily": {
            "task": "itk_academy.sync_events",
            "schedule": crontab(hour=settings.sync_hour_utc, minute=0),
        },
    },
)
