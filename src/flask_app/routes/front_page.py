import json

from fastapi import APIRouter, HTTPException, Query

from flask_app.connections import redis_conn


def create_front_page_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/leaderboard")
    async def leaderboard(
        mode: str = Query(
            "Splat Zones", description="Game mode for the leaderboard"
        ),
        region: str = Query(
            "Tentatek", description="Region for the leaderboard"
        ),
    ):
        region_bool = "Takoroka" if region == "Takoroka" else "Tentatek"

        redis_key = f"leaderboard_data:{mode}:{region_bool}"
        players = redis_conn.get(redis_key)

        if players is None:
            raise HTTPException(
                status_code=503,
                detail="Data is not available yet, please wait.",
            )
        else:
            players = json.loads(players)
            return {"players": players}

    return router
