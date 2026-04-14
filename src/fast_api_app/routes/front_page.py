import orjson
from fastapi import APIRouter, HTTPException, Query

from fast_api_app.connections import redis_conn, sqlite_cursor
from shared_lib.queries.leaderboard_queries import (
    ARCHIVED_LEADERBOARD_SEASONS_SQLITE_QUERY,
    ARCHIVED_LEADERBOARD_SQLITE_QUERY,
)
from shared_lib.utils import get_weapon_image

router = APIRouter()


def _players_to_columnar(players: list[dict]) -> dict[str, list]:
    out: dict[str, list] = {}
    for player in players:
        for key, value in player.items():
            if key not in out:
                out[key] = []
            out[key].append(value)
    return out


def _get_available_archive_seasons() -> list[int]:
    results = sqlite_cursor.execute(ARCHIVED_LEADERBOARD_SEASONS_SQLITE_QUERY)
    return [
        row[0]
        for row in results.fetchall()
        if row[0] is not None and row[0] >= 1
    ]


@router.get("/api/leaderboard")
async def leaderboard(
    mode: str = Query(
        "Splat Zones", description="Game mode for the leaderboard"
    ),
    region: str = Query("Tentatek", description="Region for the leaderboard"),
):
    redis_key = f"leaderboard_data:{mode}:{region}"
    players = redis_conn.get(redis_key)

    if players is None:
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )
    else:
        players: list[dict] = orjson.loads(players)
        return {"players": _players_to_columnar(players)}


@router.get("/api/leaderboard/archive", summary="Get archived leaderboard")
async def archived_leaderboard(
    mode: str = Query(
        "Splat Zones", description="Game mode for the leaderboard"
    ),
    region: str = Query("Tentatek", description="Region for the leaderboard"),
    season: int | None = Query(
        None,
        ge=1,
        description="Completed season number for the archived leaderboard",
    ),
):
    available_seasons = _get_available_archive_seasons()
    if not available_seasons:
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )

    selected_season = (
        season if season in available_seasons else available_seasons[0]
    )
    region_bool = region.lower() == "takoroka"
    results = sqlite_cursor.execute(
        ARCHIVED_LEADERBOARD_SQLITE_QUERY,
        {
            "mode": mode,
            "region": int(region_bool),
            "season_number": selected_season + 1,
        },
    )
    rows = results.fetchall()
    columns = [desc[0] for desc in sqlite_cursor.description]

    players = []
    for row in rows:
        player = {column: row[idx] for idx, column in enumerate(columns)}
        player["weapon_image"] = get_weapon_image(int(player["weapon_id"]))
        players.append(player)

    return {
        "players": _players_to_columnar(players),
        "mode": mode,
        "region": region,
        "season_number": selected_season,
        "available_seasons": available_seasons,
    }
