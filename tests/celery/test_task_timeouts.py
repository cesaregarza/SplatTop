import importlib

import pytest


def test_tasks_have_time_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")

    app_module = importlib.import_module("celery_app.app")
    importlib.reload(app_module)
    celery = app_module.celery

    for task_name, task in celery.tasks.items():
        if task_name.startswith("celery."):
            continue
        assert task.time_limit is not None, f"{task_name} missing time_limit"
        assert (
            task.soft_time_limit is not None
        ), f"{task_name} missing soft_time_limit"
