import logging

import orjson
from fastapi import APIRouter, HTTPException, Query

from fast_api_app.connections import redis_conn
from shared_lib.constants import (
    ALIASES_REDIS_KEY,
    SEASON_RESULTS_REDIS_KEY,
    WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
)
from shared_lib.utils import get_weapon_image

logger = logging.getLogger(__name__)

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
    final_results: bool = Query(
        False, description="Whether to show final results or not"
    ),
):
    logger.info(
        "Fetching weapon leaderboard for weapon_id: %d, mode: %s, region: %s, additional_weapon_id: %s, min_threshold: %d, final_results: %s",
        weapon_id,
        mode,
        region,
        additional_weapon_id,
        min_threshold,
        final_results,
    )

    out_cols = [
        "player_id",
        "season_number",
        "max_x_power",
        "games_played",
        "percent_games_played",
    ]
    region_bool = region == "Takoroka"
    players = redis_conn.get(WEAPON_LEADERBOARD_PEAK_REDIS_KEY)
    if final_results:
        results = redis_conn.get(SEASON_RESULTS_REDIS_KEY)
        if results is None:
            logger.error("Season results data is not available yet.")
            raise HTTPException(
                status_code=503,
                detail="Data is not available yet, please wait.",
            )

    if players is None:
        logger.error("Weapon leaderboard data is not available yet.")
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )

    aliases = redis_conn.get(ALIASES_REDIS_KEY)
    if aliases is None:
        logger.error("Aliases data is not available yet.")
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )
    aliases = orjson.loads(aliases)
    latest_aliases = {}
    for alias in aliases:
        player_id = alias["player_id"]
        if (
            player_id not in latest_aliases
            or alias["last_seen"] > latest_aliases[player_id]["last_seen"]
        ):
            latest_aliases[player_id] = alias
    aliases = {
        alias["player_id"]: alias["splashtag"]
        for alias in latest_aliases.values()
    }
    del latest_aliases

    players: list[dict] = orjson.loads(players)
    out: dict[str, list] = {}
    player_xref: dict[tuple[str, ...], dict] = {}

    def skip_row_conditions(player: dict) -> bool:
        return not (
            player["weapon_id"] in (weapon_id, additional_weapon_id)
            and player["mode"] == mode
            and (player["region"] is region_bool or region == "Any")
            and player["percent_games_played"] >= (min_threshold / 1000)
        )

    for player in players:
        player_xref[
            (
                player["player_id"],
                player["mode"],
                player["region"],
                player["season_number"],
            )
        ] = player
        if final_results:
            continue
        if skip_row_conditions(player):
            continue
        for key, value in player.items():
            if key not in out_cols:
                continue
            if key not in out:
                out[key] = []
            out[key].append(value)
        if "splashtag" not in out:
            out["splashtag"] = []
        out["splashtag"].append(aliases.get(player["player_id"], ""))

    if final_results:
        results: list[dict] = orjson.loads(results)
        for result in results:
            player_id = result["player_id"]
            mode = result["mode"]
            region = result["region"]
            season_number = result["season_number"]
            player = player_xref.get(
                (player_id, mode, region, season_number), {}
            )
            if not player or skip_row_conditions(player):
                continue
            for key, value in result.items():
                if key not in out_cols:
                    continue
                if key not in out:
                    out[key] = []
                out[key].append(value)
            if "percent_games_played" not in out:
                out["percent_games_played"] = []
            out["percent_games_played"].append(player["percent_games_played"])
            if "splashtag" not in out:
                out["splashtag"] = []
            out["splashtag"].append(aliases.get(player["player_id"], ""))

    logger.info(
        "Successfully fetched weapon leaderboard for weapon_id: %d", weapon_id
    )
    return {
        "players": out,
        "region": region,
        "mode": mode,
        "weapon_id": weapon_id,
        "weapon_image": get_weapon_image(weapon_id),
    }
