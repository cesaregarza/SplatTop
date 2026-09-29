import base64
import hashlib
import sqlite3
import zlib
from collections import Counter

import orjson
import pytest

from shared_lib.constants import (
    ALIASES_REDIS_KEY,
    LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY,
    LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY,
    LOOKUP_SQLITE_SNAPSHOT_META_KEY,
    SEASON_RESULTS_REDIS_KEY,
    WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
)
from shared_lib.monitoring import render_latest

SOURCE_KEYS = (
    ALIASES_REDIS_KEY,
    WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
    SEASON_RESULTS_REDIS_KEY,
)


@pytest.fixture(autouse=True)
def _database_environment(monkeypatch):
    for key, value in {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_USER": "user",
        "DB_PASSWORD": "pass",
        "DB_NAME": "db",
        "RANKINGS_DB_NAME": "db",
    }.items():
        monkeypatch.setenv(key, value)


@pytest.fixture()
def snapshot_task(fake_redis, monkeypatch):
    from celery_app.tasks import sqlite_lookup_snapshot as snapshot_mod

    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis)
    for key in SOURCE_KEYS:
        fake_redis.set(key, b"[]")
    return snapshot_mod


def test_refresh_lookup_sqlite_snapshot_builds_and_reuses_artifact(
    fake_redis, monkeypatch, tmp_path
):
    from celery_app.tasks import sqlite_lookup_snapshot as snapshot_mod

    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis)

    fake_redis.set(
        ALIASES_REDIS_KEY,
        orjson.dumps(
            [
                {
                    "splashtag": "Alpha",
                    "player_id": "p1",
                    "last_seen": "2026-04-01T00:00:00Z",
                }
            ]
        ),
    )
    fake_redis.set(
        WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
        orjson.dumps(
            [
                {
                    "player_id": "p1",
                    "season_number": 1,
                    "mode": "Splat Zones",
                    "region": False,
                    "weapon_id": 101,
                    "max_x_power": 2500.0,
                    "games_played": 50,
                    "percent_games_played": 0.75,
                }
            ]
        ),
    )
    fake_redis.set(
        SEASON_RESULTS_REDIS_KEY,
        orjson.dumps(
            [
                {
                    "player_id": "p1",
                    "season_number": 2,
                    "mode": "Splat Zones",
                    "region": False,
                    "weapon_id": 101,
                    "x_power": 2600.0,
                    "rank": 5,
                }
            ]
        ),
    )

    first = snapshot_mod.refresh_lookup_sqlite_snapshot()
    assert first["rebuilt"] is True
    assert first["row_counts"] == {
        "aliases": 1,
        "weapon_leaderboard_peak": 1,
        "season_results": 1,
    }

    meta = orjson.loads(fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_META_KEY))
    assert meta["row_counts"] == first["row_counts"]
    blob = fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY)
    assert blob
    sqlite_bytes = zlib.decompress(base64.b64decode(blob))
    assert first["bytes"] == {
        "sqlite": len(sqlite_bytes),
        "compressed": len(base64.b64decode(blob)),
        "encoded": len(blob),
    }
    snapshot_path = tmp_path / "lookup.sqlite3"
    snapshot_path.write_bytes(sqlite_bytes)

    connection = sqlite3.connect(snapshot_path)
    try:
        assert connection.execute("SELECT * FROM aliases").fetchall() == [
            ("Alpha", "p1", "2026-04-01T00:00:00Z")
        ]
        assert connection.execute(
            "SELECT * FROM weapon_leaderboard_peak"
        ).fetchall() == [("p1", 1, "Splat Zones", 0, 101, 2500.0, 50, 0.75)]
        assert connection.execute(
            "SELECT * FROM season_results"
        ).fetchall() == [("p1", 2, "Splat Zones", 0, 101, 2600.0, 5)]
    finally:
        connection.close()

    second = snapshot_mod.refresh_lookup_sqlite_snapshot()
    assert second == {
        "rebuilt": False,
        "reason": "unchanged",
        "version": meta["version"],
    }
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY) is None
    assert (
        'lookup_sqlite_snapshot_last_success_timestamp_seconds{kind="build"}'
        in render_latest().decode("utf-8")
    )


@pytest.mark.parametrize("decode_responses", [False, True])
def test_each_source_is_read_once_without_decoding_unchanged_json(
    snapshot_task, fake_redis, monkeypatch, decode_responses
):
    original_get = fake_redis.get
    calls = Counter()

    def get(key):
        calls[key] += 1
        value = original_get(key)
        if decode_responses and isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    monkeypatch.setattr(fake_redis, "get", get)
    first = snapshot_task.refresh_lookup_sqlite_snapshot()
    assert first["rebuilt"]
    assert all(calls[key] == 1 for key in SOURCE_KEYS)
    assert original_get(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY) is None
    calls.clear()
    original_loads = orjson.loads

    def loads(value):
        assert value not in (b"[]", "[]"), "Unchanged source was decoded"
        return original_loads(value)

    monkeypatch.setattr(orjson, "loads", loads)
    second = snapshot_task.refresh_lookup_sqlite_snapshot()
    assert second == {
        "rebuilt": False,
        "reason": "unchanged",
        "version": first["version"],
    }
    assert all(calls[key] == 1 for key in SOURCE_KEYS)
    assert original_get(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY) is None


def test_source_change_rebuilds_from_the_bytes_that_were_hashed(
    snapshot_task, fake_redis, monkeypatch, tmp_path
):
    first = snapshot_task.refresh_lookup_sqlite_snapshot()
    alias = {"splashtag": "Alpha", "player_id": "p1", "last_seen": "2026-09-07"}
    source = orjson.dumps([alias])
    fake_redis.set(ALIASES_REDIS_KEY, source)
    original_get = fake_redis.get

    def get(key):
        value = original_get(key)
        if key == ALIASES_REDIS_KEY:
            # A producer replaces the source immediately after this read.
            fake_redis.set(key, b"[]")
        return value

    monkeypatch.setattr(fake_redis, "get", get)
    second = snapshot_task.refresh_lookup_sqlite_snapshot()
    assert second["rebuilt"] and second["version"] != first["version"]
    meta = orjson.loads(original_get(LOOKUP_SQLITE_SNAPSHOT_META_KEY))
    assert (
        meta["source_hashes"]["aliases"] == hashlib.sha256(source).hexdigest()
    )
    blob = original_get(LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY)
    db_path = tmp_path / "changed.sqlite3"
    db_path.write_bytes(zlib.decompress(base64.b64decode(blob)))
    connection = sqlite3.connect(db_path)
    try:
        assert connection.execute("SELECT * FROM aliases").fetchall() == [
            ("Alpha", "p1", "2026-09-07")
        ]
    finally:
        connection.close()


@pytest.mark.parametrize("existing_meta", [b"invalid", b"[]", None])
def test_invalid_or_missing_metadata_rebuilds(
    snapshot_task, fake_redis, existing_meta
):
    snapshot_task.refresh_lookup_sqlite_snapshot()
    if existing_meta is None:
        fake_redis.delete(LOOKUP_SQLITE_SNAPSHOT_META_KEY)
    else:
        fake_redis.set(LOOKUP_SQLITE_SNAPSHOT_META_KEY, existing_meta)
    assert snapshot_task.refresh_lookup_sqlite_snapshot()["rebuilt"]


def test_schema_change_rebuilds_unchanged_sources(snapshot_task, fake_redis):
    snapshot_task.refresh_lookup_sqlite_snapshot()
    meta = orjson.loads(fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_META_KEY))
    meta["schema_version"] = -1
    fake_redis.set(LOOKUP_SQLITE_SNAPSHOT_META_KEY, orjson.dumps(meta))
    assert snapshot_task.refresh_lookup_sqlite_snapshot()["rebuilt"]


@pytest.mark.parametrize(
    "key,label",
    [
        (ALIASES_REDIS_KEY, "Alias"),
        (WEAPON_LEADERBOARD_PEAK_REDIS_KEY, "Weapon leaderboard"),
        (SEASON_RESULTS_REDIS_KEY, "Season results"),
    ],
)
@pytest.mark.parametrize("invalid_value", [b"invalid", b"{}"])
def test_invalid_source_preserves_published_artifact_and_releases_lock(
    snapshot_task, fake_redis, key, label, invalid_value
):
    snapshot_task.refresh_lookup_sqlite_snapshot()
    old_meta = fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_META_KEY)
    old_blob = fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY)
    fake_redis.set(key, invalid_value)
    message = (
        "Invalid JSON payload"
        if invalid_value == b"invalid"
        else f"{label} payload is not a list"
    )
    with pytest.raises(RuntimeError, match=message):
        snapshot_task.refresh_lookup_sqlite_snapshot()
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_META_KEY) == old_meta
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY) == old_blob
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY) is None


def test_missing_source_preserves_existing_artifact(snapshot_task, fake_redis):
    snapshot_task.refresh_lookup_sqlite_snapshot()
    old_meta = fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_META_KEY)
    old_blob = fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY)
    fake_redis.delete(WEAPON_LEADERBOARD_PEAK_REDIS_KEY)
    result = snapshot_task.refresh_lookup_sqlite_snapshot()
    assert result == {
        "rebuilt": False,
        "reason": "source_missing",
        "missing_keys": [WEAPON_LEADERBOARD_PEAK_REDIS_KEY],
    }
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_META_KEY) == old_meta
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY) == old_blob
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY) is None


def test_lock_miss_does_not_read_sources(
    snapshot_task, fake_redis, monkeypatch
):
    fake_redis.set(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY, b"other-worker")
    original_get = fake_redis.get

    def get(key):
        assert key not in SOURCE_KEYS
        return original_get(key)

    monkeypatch.setattr(fake_redis, "get", get)
    assert snapshot_task.refresh_lookup_sqlite_snapshot() == {
        "rebuilt": False,
        "reason": "lock_missed",
    }
    assert original_get(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY) == b"other-worker"


def test_refresh_lookup_sqlite_snapshot_skips_when_sources_missing(
    fake_redis, monkeypatch
):
    from celery_app.tasks import sqlite_lookup_snapshot as snapshot_mod

    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis)

    result = snapshot_mod.refresh_lookup_sqlite_snapshot()

    assert result == {
        "rebuilt": False,
        "reason": "source_missing",
        "missing_keys": [
            ALIASES_REDIS_KEY,
            WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
            SEASON_RESULTS_REDIS_KEY,
        ],
    }
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_META_KEY) is None
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY) is None
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY) is None
