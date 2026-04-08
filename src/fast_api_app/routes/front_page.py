import orjson
from fastapi import APIRouter, HTTPException, Query

from fast_api_app.connections import redis_conn
from shared_lib.constants import RACE_TO_5000_REDIS_KEY

router = APIRouter()


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
        out: dict[str, list] = {}
        for player in players:
            for key, value in player.items():
                if key not in out:
                    out[key] = []
                out[key].append(value)
        return {"players": out}


@router.get("/api/race-to-5000")
async def race_to_5000():
    race_data = redis_conn.get(RACE_TO_5000_REDIS_KEY)

    if race_data is None:
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )

    return orjson.loads(race_data)
