from celery import Celery
from celery.schedules import crontab

celery = Celery(
    "tasks", broker="redis://redis:6379", backend="redis://redis:6379"
)

celery.conf.beat_schedule = {
    "pull-data-every-ten-minutes": {
        "task": "tasks.pull_data",
        "schedule": crontab(minute="*/10"),
    },
}
