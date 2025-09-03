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
    "update-lorenz-and-gini-ten-minutes": {
        "task": "tasks.update_lorenz_and_gini",
        "schedule": crontab(minute="*/10"),
    },
    "fetch-weapon-leaderboard-every-ten-minutes": {
        "task": "tasks.fetch_weapon_leaderboard",
        "schedule": crontab(minute="5-59/10"),
    },
    "fetch-season-results-every-hour": {
        "task": "tasks.fetch_season_results",
        "schedule": crontab(minute=30, hour="*"),
    },
    "flush-api-usage-every-minute": {
        "task": "tasks.flush_api_usage",
        "schedule": crontab(minute="*"),
    },
}
