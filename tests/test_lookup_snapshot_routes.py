import asyncio
import base64
import zlib

import orjson
from starlette.requests import Request

from shared_lib.constants import (
    LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY,
    LOOKUP_SQLITE_SNAPSHOT_META_KEY,
)
from shared_lib.sqlite_lookup_snapshot import (
    LOOKUP_SNAPSHOT_SCHEMA_VERSION,
    create_lookup_snapshot_database,
    populate_lookup_snapshot_database,
)


def _publish_lookup_snapshot(fake_redis, tmp_path):
    db_path = tmp_path / "lookup.sqlite3"
    connection = create_lookup_snapshot_database(db_path)
    try:
        row_counts = populate_lookup_snapshot_database(
            connection,
            aliases=[
                {
                    "splashtag": "Alpha",
                    "player_id": "p1",
                    "last_seen": "2026-04-01T00:00:00Z",
                }
            ],
            weapon_rows=[
                {
                    "player_id": "p1",
                    "season_number": 2,
                    "mode": "Splat Zones",
                    "region": False,
                    "weapon_id": 101,
                    "max_x_power": 2500.0,
                    "games_played": 50,
                    "percent_games_played": 0.75,
                }
            ],
            season_rows=[
                {
                    "player_id": "p1",
                    "season_number": 3,
                    "mode": "Splat Zones",
                    "region": False,
                    "weapon_id": 101,
                    "x_power": 2515.2,
                    "rank": 12,
                }
            ],
        )
    finally:
        connection.close()

    sqlite_bytes = db_path.read_bytes()
    fake_redis.set(
        LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY,
        base64.b64encode(zlib.compress(sqlite_bytes, level=6)).decode("ascii"),
    )
    fake_redis.set(
        LOOKUP_SQLITE_SNAPSHOT_META_KEY,
        orjson.dumps(
            {
                "version": "test-v1",
                "schema_version": LOOKUP_SNAPSHOT_SCHEMA_VERSION,
                "compression": "zlib",
                "encoding": "base64",
                "row_counts": row_counts,
            }
        ),
    )


def test_search_route_reads_from_lookup_snapshot(
    client_factory, fake_redis, monkeypatch, tmp_path
):
    _publish_lookup_snapshot(fake_redis, tmp_path)

    with client_factory(redis=fake_redis) as client:
        import fast_api_app.routes.search as search_mod

        monkeypatch.setattr(search_mod, "redis_conn", fake_redis)
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/search/Al",
                "headers": [],
                "client": ("203.0.113.17", 12345),
                "app": client.app,
            }
        )
        result = asyncio.run(
            search_mod.search.__wrapped__(
                query="Al",
                request=request,
            )
        )

    assert result == [("Alpha", "p1")]


def test_weapon_leaderboard_route_reads_from_lookup_snapshot(
    client_factory, fake_redis, monkeypatch, tmp_path
):
    _publish_lookup_snapshot(fake_redis, tmp_path)

    with client_factory(redis=fake_redis) as client:
        import fast_api_app.routes.weapon_leaderboard as route_mod

        monkeypatch.setattr(
            route_mod,
            "get_weapon_image",
            lambda weapon_id: f"weapon:{weapon_id}",
        )

        response = client.get(
            "/api/weapon-leaderboard/101?mode=Splat%20Zones&region=Tentatek&min_threshold=500"
        )

    assert response.status_code == 200
    assert response.json()["players"]["player_id"] == ["p1"]
    assert response.json()["players"]["alias"] == ["Alpha"]
    assert response.json()["weapon_image"] == "weapon:101"
