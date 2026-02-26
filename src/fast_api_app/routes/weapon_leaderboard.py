import logging

from fastapi import APIRouter, HTTPException, Query

from fast_api_app.connections import sqlite_cursor
from shared_lib.queries.leaderboard_queries import (
    SEASON_RESULTS_SQLITE_QUERY,
    WEAPON_LEADERBOARD_SQLITE_QUERY,
)
from shared_lib.utils import get_weapon_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["weapon-leaderboard"])


@router.get(
    "/weapon-leaderboard/{weapon_id}",
    summary="Get weapon leaderboard",
)
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
    final_results: bool = Query(
        False, description="Whether to show final results or not"
    ),
):
    logger.info(
        "Fetching weapon leaderboard for weapon_id: %d, "
        "mode: %s, region: %s, additional_weapon_id: %s, min_threshold: %d, "
        "final_results: %s",
        weapon_id,
        mode,
        region,
        additional_weapon_id,
        min_threshold,
        final_results,
    )

    region_bool = region.lower() == "takoroka"
    min_threshold /= 1000

    if final_results:
        query = SEASON_RESULTS_SQLITE_QUERY
        params = {
            "mode": mode,
            "region": int(region_bool),
            "min_threshold": min_threshold,
            "weapon_id": weapon_id,
            "additional_weapon_id": additional_weapon_id,
        }
    else:
        query = WEAPON_LEADERBOARD_SQLITE_QUERY
        params = {
            "mode": mode,
            "region": int(region_bool),
            "min_threshold": min_threshold,
            "weapon_id": weapon_id,
            "additional_weapon_id": additional_weapon_id,
        }

    results = sqlite_cursor.execute(query, params)
    result = results.fetchall()
    if not result:
        check_if_data_available = sqlite_cursor.execute(
            "SELECT COUNT(*) FROM weapon_leaderboard_peak"
        )
        if not check_if_data_available.fetchone()[0]:
            logger.error(
                "No data found for weapon_id: %d, mode: %s, region: %s, "
                "additional_weapon_id: %s, min_threshold: %d, final_results: %s",
                weapon_id,
                mode,
                region,
                additional_weapon_id,
                min_threshold,
                final_results,
            )
            raise HTTPException(
                status_code=503,
                detail="Data is not available yet, please wait.",
            )
        else:
            logger.info("No data found for weapon_id: %d", weapon_id)
            return {"players": {}, "mode": mode, "region": bool(region)}

    columns = [desc[0] for desc in sqlite_cursor.description]
    out = {"players": {}}
    for column in columns:
        if column in ["mode", "region"]:
            continue
        out["players"][column] = [row[columns.index(column)] for row in result]
    out["weapon_image"] = get_weapon_image(weapon_id)
    if additional_weapon_id:
        out["additional_weapon_image"] = get_weapon_image(additional_weapon_id)
    out["mode"] = mode
    out["region"] = bool(region)
    return out
