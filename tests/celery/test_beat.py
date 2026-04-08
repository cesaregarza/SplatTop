import importlib

from celery.schedules import crontab


def test_fetch_race_to_5000_runs_every_ten_minutes():
    beat_mod = importlib.import_module("celery_app.beat")
    beat_mod = importlib.reload(beat_mod)

    entry = beat_mod.celery.conf.beat_schedule[
        "fetch-race-to-5000-every-ten-minutes"
    ]

    assert entry["task"] == "tasks.fetch_race_to_5000"
    assert repr(entry["schedule"]) == repr(crontab(minute="*/10"))
