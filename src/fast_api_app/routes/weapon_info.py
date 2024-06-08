import orjson
from fastapi import APIRouter, HTTPException

from fast_api_app.connections import redis_conn
from shared_lib.constants import (
    GAME_TRANSLATION_REDIS_KEY,
    GINI_COEFF_REDIS_KEY,
    LORENZ_CURVE_REDIS_KEY,
    SKILL_OFFSET_REDIS_KEY,
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


@router.get("/api/skill_offset")
async def skill_offset():
    skill_offset = redis_conn.get(SKILL_OFFSET_REDIS_KEY)
    if skill_offset is None:
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )
    else:
        skill_offset = orjson.loads(skill_offset)
        return skill_offset


@router.get("/api/lorenz")
async def lorenz():
    lorenz = redis_conn.get(LORENZ_CURVE_REDIS_KEY)
    gini = redis_conn.get(GINI_COEFF_REDIS_KEY)
    if lorenz is None:
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )
    else:
        lorenz = orjson.loads(lorenz)
        gini = orjson.loads(gini)
        return {"lorenz": lorenz, "gini": gini}
