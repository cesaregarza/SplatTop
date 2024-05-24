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
    "pull-aliases-every-ten-minutes": {
        "task": "tasks.pull_aliases",
        "schedule": crontab(minute="*/10"),
    },
    "update-skill-offset-every-ten-minutes": {
        "task": "tasks.update_skill_offset",
        "schedule": crontab(minute="*/10"),
    },
}
