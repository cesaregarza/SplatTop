import base64
import sqlite3
import zlib

import orjson

from shared_lib.constants import (
    ALIASES_REDIS_KEY,
    LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY,
    LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY,
    LOOKUP_SQLITE_SNAPSHOT_META_KEY,
    SEASON_RESULTS_REDIS_KEY,
    WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
)


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
    snapshot_path = tmp_path / "lookup.sqlite3"
    snapshot_path.write_bytes(sqlite_bytes)

    connection = sqlite3.connect(snapshot_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM aliases").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM weapon_leaderboard_peak"
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM season_results"
            ).fetchone()[0]
            == 1
        )
    finally:
        connection.close()

    second = snapshot_mod.refresh_lookup_sqlite_snapshot()
    assert second == {
        "rebuilt": False,
        "reason": "unchanged",
        "version": meta["version"],
    }
    assert fake_redis.get(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY) is None


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
