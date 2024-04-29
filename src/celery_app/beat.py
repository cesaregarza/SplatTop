from celery import Celery
from celery.schedules import crontab

from shared_lib.constants import REDIS_URI

celery = Celery("tasks", broker=REDIS_URI, backend=REDIS_URI)

celery.conf.beat_schedule = {
    "pull-data-every-ten-minutes": {
        "task": "tasks.pull_data",
        "schedule": crontab(minute="*/10"),
    },
    "update-weapon-info-every-hour": {
        "task": "tasks.update_weapon_info",
        "schedule": crontab(minute=0, hour="*"),
    },
}
