import orjson
from fastapi import APIRouter, HTTPException, Query

from fast_api_app.connections import redis_conn

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
