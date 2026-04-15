import orjson
from fastapi import APIRouter, HTTPException, Query

from fast_api_app.connections import redis_conn
from shared_lib.constants import (
    GAME_TRANSLATION_REDIS_KEY,
    GINI_COEFF_REDIS_KEY,
    LORENZ_CURVE_REDIS_KEY,
    MODES,
    REGIONS,
    SKILL_OFFSET_REDIS_KEY,
    WEAPON_INFO_REDIS_KEY,
)

router = APIRouter(prefix="/api", tags=["weapon-info"])
ALL_SLICE_KEY = "all"


@router.get("/weapon-info", summary="Get weapon reference data")
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


@router.get("/game-translation", summary="Get game translation data")
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


def select_skill_offset_slice(
    payload: list | dict, mode: str | None, region: str | None
) -> list:
    if isinstance(payload, list):
        if mode or region:
            raise HTTPException(
                status_code=503,
                detail="Skill offset slices are not available yet, please wait.",
            )
        return payload

    if mode is not None and mode not in MODES:
        raise HTTPException(
            status_code=404, detail="Skill offset slice not found."
        )

    if region is not None and region not in REGIONS:
        raise HTTPException(
            status_code=404, detail="Skill offset slice not found."
        )

    mode_key = mode or ALL_SLICE_KEY
    region_key = region or ALL_SLICE_KEY
    selected_slice = payload.get(mode_key, {}).get(region_key)
    if selected_slice is None:
        raise HTTPException(
            status_code=404, detail="Skill offset slice not found."
        )

    return selected_slice


@router.get("/skill-offset", summary="Get skill offset data")
async def skill_offset(
    mode: str | None = Query(default=None),
    region: str | None = Query(default=None),
):
    skill_offset = redis_conn.get(SKILL_OFFSET_REDIS_KEY)
    if skill_offset is None:
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )
    else:
        skill_offset_payload = orjson.loads(skill_offset)
        return select_skill_offset_slice(skill_offset_payload, mode, region)


@router.get("/lorenz", summary="Get Lorenz curve and Gini coefficient")
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
