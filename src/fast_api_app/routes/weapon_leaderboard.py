import orjson
from fastapi import APIRouter, HTTPException, Query

from fast_api_app.connections import redis_conn
from shared_lib.constants import WEAPON_LEADERBOARD_REDIS_KEY
from shared_lib.utils import get_weapon_image

router = APIRouter()


@router.get("/api/weapon_leaderboard/{weapon_id}")
async def weapon_leaderboard(
    weapon_id: int,
    mode: str = Query(
        "Splat Zones", description="Game mode for the leaderboard"
    ),
    region: str = Query("Tentatek", description="Region for the leaderboard"),
    additional_weapon_id: int = Query(
        None, description="Additional weapon id for comparison"
    ),
    min_threshold: int = Query(
        500, description="Minimum threshold for showing a weapon, 500 means 50%"
    ),
):
    region_bool = region == "Takoroka"
    players = redis_conn.get(WEAPON_LEADERBOARD_REDIS_KEY)
    if players is None:
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )
    else:
        players: list[dict] = orjson.loads(players)
        out: dict[str, list] = {}
        for player in players:
            if player["weapon_id"] not in (weapon_id, additional_weapon_id):
                continue
            if player["mode"] != mode:
                continue
            if (player["region"] is region_bool) and (region != "Any"):
                continue
            if player["percent_games_played"] < (min_threshold / 1000):
                continue
            for key, value in player.items():
                if key not in out:
                    out[key] = []
                out[key].append(value)

    return {"players": out, "weapon_image": get_weapon_image(weapon_id)}
