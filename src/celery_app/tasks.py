import logging

import orjson
import pandas as pd
import redis
import requests
from celery import Celery
from sqlalchemy import text

from celery_app.database import Session
from shared_lib.constants import (
    ALIASES_REDIS_KEY,
    GAME_TRANSLATION_BASE_URL,
    GAME_TRANSLATION_REDIS_KEY,
    LANGUAGES,
    MODES,
    PLAYER_DATA_REDIS_KEY,
    PLAYER_LATEST_REDIS_KEY,
    PLAYER_PUBSUB_CHANNEL,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_URI,
    REGIONS,
    WEAPON_INFO_REDIS_KEY,
    WEAPON_INFO_URL,
    WEAPON_LEADERBOARD_FLOOR,
    WEAPON_LEADERBOARD_THRESHOLD,
    WEAPON_LEADERBOARD_REDIS_KEY,
)
from shared_lib.queries.front_page_queries import LEADERBOARD_MAIN_QUERY
from shared_lib.queries.misc_queries import (
    ALIAS_QUERY,
    WEAPON_LEADERBOARD_QUERY,
)
from shared_lib.queries.player_queries import (
    PLAYER_DATA_QUERY,
    PLAYER_LATEST_QUERY,
    SEASON_RESULTS_QUERY,
)
from shared_lib.utils import get_badge_image, get_banner_image, get_weapon_image

celery = Celery("tasks", broker=REDIS_URI, backend=REDIS_URI)

# Establish a connection to Redis
redis_conn = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True
)


def fetch_and_store_leaderboard_data(mode: str, region_bool: bool) -> None:
    query = text(LEADERBOARD_MAIN_QUERY)
    with Session() as session:
        result = session.execute(
            query, {"mode": mode, "region": region_bool}
        ).fetchall()
        players = [{**row._asdict()} for row in result]

    for player in players:
        player["weapon_image"] = get_weapon_image(int(player["weapon_id"]))
        player["badge_left_image"] = get_badge_image(player["badge_left_id"])
        player["badge_center_image"] = get_badge_image(
            player["badge_center_id"]
        )
        player["badge_right_image"] = get_badge_image(player["badge_right_id"])
        player["nameplate_image"] = get_banner_image(
            int(player["nameplate_id"])
        )
        player["timestamp"] = player["timestamp"].isoformat()
        player["rotation_start"] = player["rotation_start"].isoformat()

    # Save to Redis with a key that combines mode and region for uniqueness
    redis_key = (
        f"leaderboard_data:{mode}:{'Takoroka' if region_bool else 'Tentatek'}"
    )
    redis_conn.set(redis_key, orjson.dumps(players))


@celery.task(name="tasks.pull_data")
def pull_data() -> None:
    for mode in MODES:
        for region in REGIONS:
            region_bool = region == "Takoroka"
            fetch_and_store_leaderboard_data(mode, region_bool)


@celery.task(name="tasks.fetch_player_data")
def fetch_player_data(player_id: str) -> None:
    logging.info("Running task: fetch_player_data for player_id: %s", player_id)
    task_signature = f"fetch_player_data:{player_id}"
    already_running = redis_conn.get(task_signature)

    if already_running:
        logging.info("Task already running. Skipping.")
        return
    else:
        redis_conn.set(task_signature, "true", ex=60)

    cache_key = f"{PLAYER_LATEST_REDIS_KEY}:{player_id}"

    if redis_conn.exists(cache_key):
        logging.info("Data already exists in cache. Skipping fetch.")
    else:
        player_result = _fetch_player_data(player_id)
        season_result = _fetch_season_data(player_id)
        result = {
            "player_data": player_result,
            "aggregated_data": aggregate_player_data(
                player_result, season_result, player_id
            ),
        }
        redis_conn.set(cache_key, orjson.dumps(result), ex=60)

    # Publish the data to the player_data_channel
    redis_conn.publish(
        PLAYER_PUBSUB_CHANNEL,
        orjson.dumps(
            {"player_id": player_id, "key": cache_key, "type": "data"}
        ),
    )
    try:
        redis_conn.delete(task_signature)
    except Exception as e:
        logging.error(f"Error deleting task signature: {e}")
        logging.error("Probably expired before deletion. Proceeding.")


def _fetch_player_data(player_id: str) -> list[dict]:
    base_query = text(PLAYER_DATA_QUERY)
    with Session() as session:
        result = session.execute(
            base_query, {"player_id": player_id}
        ).fetchall()

    result = [{**row._asdict()} for row in result]
    for player in result:
        player["timestamp"] = player["timestamp"].isoformat()
        player["rotation_start"] = player["rotation_start"].isoformat()

    return result


def _fetch_season_data(player_id: str) -> list[dict]:
    base_query = text(SEASON_RESULTS_QUERY)
    with Session() as session:
        result = session.execute(
            base_query, {"player_id": player_id}
        ).fetchall()

    result = [{**row._asdict()} for row in result]

    return result


def aggregate_player_data(
    player_data: list[dict], season_data: list[dict], player_id: str
) -> dict:
    logging.info("Aggregating player data")
    player_df = pd.DataFrame(player_data)
    weapon_counts = aggregate_weapon_counts(player_df)
    weapon_winrate = aggregate_weapon_winrate(player_df)
    agg_season_data = aggregate_season_data(player_df)
    latest_data = pull_all_latest_data(player_id)
    return {
        "weapon_counts": weapon_counts,
        "weapon_winrate": weapon_winrate,
        "season_results": season_data,
        "aggregate_season_data": agg_season_data,
        "latest_data": latest_data,
    }


def aggregate_weapon_counts(player_df: pd.DataFrame) -> list[dict]:
    return (
        player_df.query("updated")
        .sort_values("timestamp", ascending=False)
        .groupby(["mode", "weapon_id", "season_number"])["rank"]
        .count()
        .reset_index()
        .rename(columns={"rank": "count"})
        .to_dict(orient="records")
    )


def aggregate_weapon_winrate(player_df: pd.DataFrame) -> list[dict]:
    out_df = player_df.query("updated")
    out_df["x_power_diff"] = out_df["x_power"].diff()
    # It shouldn't ever happen but filter out any x_power_diff that are 0
    out_df = out_df.loc[out_df["x_power_diff"] != 0]
    out_df["win"] = out_df["x_power_diff"] > 0
    return (
        out_df.groupby(["mode", "weapon_id", "season_number"])["win"]
        .agg(["sum", "count"])
        .reset_index()
        .rename(columns={"win": "win_count", "count": "total_count"})
        .to_dict(orient="records")
    )


def aggregate_season_data(player_df: pd.DataFrame) -> list[dict]:
    return (
        player_df.groupby(["season_number", "mode"])["x_power"]
        .max()
        .rename("peak_x_power")
        .reset_index()
        .to_dict(orient="records")
    )


def pull_all_latest_data(player_id: str) -> list[dict]:
    data = []
    for region in REGIONS:
        for mode in MODES:
            redis_key = f"leaderboard_data:{mode}:{region}"
            data.extend(orjson.loads(redis_conn.get(redis_key)))

    return (
        pd.DataFrame(data)
        .query(f"player_id == @player_id")
        .to_dict(orient="records")
    )


def calculate_latest_data(player_df: pd.DataFrame) -> dict:
    latest_timestamps = player_df.groupby("mode")["timestamp"].max()
    latest_data = player_df[
        player_df["timestamp"].isin(latest_timestamps)
    ].to_dict(orient="records")
    return latest_data


@celery.task(name="tasks.update_weapon_info")
def update_weapon_info() -> None:
    logging.info("Running task: update_weapon_info")
    response = requests.get(WEAPON_INFO_URL)
    weapon_info = orjson.loads(response.text)
    language_data = {}
    for language in LANGUAGES:
        response = requests.get(GAME_TRANSLATION_BASE_URL % language)
        language_data[language] = orjson.loads(response.text)

    redis_conn.set(WEAPON_INFO_REDIS_KEY, orjson.dumps(weapon_info))
    logging.info("Weapon info updated in Redis.")
    redis_conn.set(GAME_TRANSLATION_REDIS_KEY, orjson.dumps(language_data))
    logging.info("Weapon translations updated in Redis.")


@celery.task(name="tasks.pull_aliases")
def pull_aliases() -> None:
    logging.info("Running task: fetch_aliases")
    query = text(ALIAS_QUERY)
    with Session() as session:
        result = session.execute(query).fetchall()

    aliases = [{**row._asdict()} for row in result]
    redis_conn.set(ALIASES_REDIS_KEY, orjson.dumps(aliases))
    logging.info("Aliases updated in Redis.")


@celery.task(name="tasks.update_weapon_leaderboard")
def update_weapon_leaderboard() -> None:
    query = text(WEAPON_LEADERBOARD_QUERY)
    with Session() as session:
        result = session.execute(query).fetchall()
        player_data = [{**row._asdict()} for row in result]

    df = pd.DataFrame(player_data)
    weapon_info = orjson.loads(redis_conn.get(WEAPON_INFO_REDIS_KEY))
    df["weapon"] = df["weapon_id"].apply(
        lambda x: (
            f"{weapon_info[str(x)]['class']}_"
            f"{weapon_info[str(x)]['reference_kit']}"
        )
    )
    count = (
        df.groupby(["player_id", "weapon", "mode", "region"])
        .size()
        .reset_index(name="count")
    )
    count["total"] = count.groupby(["player_id", "mode", "region"])[
        "count"
    ].transform("sum")
    dominant_weapons = count[
        (count["count"] > WEAPON_LEADERBOARD_FLOOR)
        & (count["count"] > count["total"] * WEAPON_LEADERBOARD_THRESHOLD)
    ]
    leaderboard = (
        dominant_weapons.groupby(["weapon", "mode", "region"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .to_dict(orient="records")
    )

    redis_conn.set(WEAPON_LEADERBOARD_REDIS_KEY, orjson.dumps(leaderboard))
