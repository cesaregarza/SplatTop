import importlib
import sys

from fastapi.testclient import TestClient


def _reload_app_modules():
    for module_name in [
        "fast_api_app.sqlite_lookup_store",
        "fast_api_app.app",
    ]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)


def test_fastapi_startup_skips_warm_tasks_by_default(
    fake_redis, monkeypatch, tmp_path
):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("COMP_AUTH_SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    monkeypatch.setenv(
        "FASTAPI_SQLITE_SNAPSHOT_DIR",
        str(tmp_path / "sqlite-lookups"),
    )
    monkeypatch.delenv("FASTAPI_ENABLE_STARTUP_WARM_TASKS", raising=False)
    monkeypatch.delenv("FASTAPI_ENABLE_LOCAL_TABLE_REFRESHERS", raising=False)

    _reload_app_modules()

    import fast_api_app.app as app_mod
    import fast_api_app.connections as conn_mod

    calls = []

    class _SpyCelery:
        def send_task(self, name, *args, **kwargs):
            calls.append(name)
            return None

    monkeypatch.setattr(conn_mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(app_mod, "celery", _SpyCelery(), raising=False)
    monkeypatch.setattr(app_mod, "start_pubsub_listener", lambda: None)

    with TestClient(app_mod.app):
        pass

    assert calls == []


def test_fastapi_startup_can_opt_into_warm_tasks(
    fake_redis, monkeypatch, tmp_path
):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("COMP_AUTH_SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    monkeypatch.setenv("COMP_LEADERBOARD_ENABLED", "true")
    monkeypatch.setenv("FASTAPI_ENABLE_STARTUP_WARM_TASKS", "true")
    monkeypatch.setenv(
        "FASTAPI_SQLITE_SNAPSHOT_DIR",
        str(tmp_path / "sqlite-lookups"),
    )

    _reload_app_modules()

    import fast_api_app.app as app_mod
    import fast_api_app.connections as conn_mod

    calls = []

    class _SpyCelery:
        def send_task(self, name, *args, **kwargs):
            calls.append(name)
            return None

    monkeypatch.setattr(conn_mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(app_mod, "celery", _SpyCelery(), raising=False)
    monkeypatch.setattr(app_mod, "start_pubsub_listener", lambda: None)

    with TestClient(app_mod.app):
        pass

    assert "tasks.pull_data" in calls
    assert "tasks.fetch_weapon_leaderboard" in calls
    assert "tasks.refresh_lookup_sqlite_snapshot" in calls
    assert "tasks.refresh_ripple_snapshots" in calls


def test_fastapi_startup_warms_tasks_by_default_in_dev_kubernetes(
    fake_redis, monkeypatch, tmp_path
):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.96.0.1")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    monkeypatch.setenv(
        "FASTAPI_SQLITE_SNAPSHOT_DIR",
        str(tmp_path / "sqlite-lookups"),
    )
    monkeypatch.delenv("FASTAPI_ENABLE_STARTUP_WARM_TASKS", raising=False)

    _reload_app_modules()

    import fast_api_app.app as app_mod
    import fast_api_app.connections as conn_mod

    calls = []

    class _SpyCelery:
        def send_task(self, name, *args, **kwargs):
            calls.append(name)
            return None

    monkeypatch.setattr(conn_mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(app_mod, "celery", _SpyCelery(), raising=False)
    monkeypatch.setattr(app_mod, "start_pubsub_listener", lambda: None)

    with TestClient(app_mod.app):
        pass

    assert "tasks.pull_aliases" in calls
    assert "tasks.fetch_weapon_leaderboard" in calls
    assert "tasks.fetch_season_results" in calls
    assert "tasks.refresh_lookup_sqlite_snapshot" in calls
