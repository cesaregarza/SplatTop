import orjson
from fastapi import APIRouter, HTTPException

from flask_app.connections import redis_conn
from shared_lib.constants import (
    GAME_TRANSLATION_REDIS_KEY,
    WEAPON_INFO_REDIS_KEY,
)

router = APIRouter()


@router.get("/api/weapon_info")
async def weapon_info():
    weapon_info = redis_conn.get(WEAPON_INFO_REDIS_KEY)
    if weapon_info is None:
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )
    else:
        weapon_info = orjson.loads(weapon_info)
        return weapon_info


@router.get("/api/game_translation")
async def game_translation():
    game_translation = redis_conn.get(GAME_TRANSLATION_REDIS_KEY)
    if game_translation is None:
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )
    else:
        game_translation = orjson.loads(game_translation)
        return game_translation
