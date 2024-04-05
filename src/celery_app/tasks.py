import json

import redis
from celery import Celery
from sqlalchemy import text

from celery_app.database import Session
from shared_lib.constants import MODES, REGIONS
from shared_lib.queries import LEADERBOARD_MAIN_QUERY
from shared_lib.utils import get_badge_image, get_banner_image, get_weapon_image

celery = Celery(
    "tasks", broker="redis://redis:6379", backend="redis://redis:6379"
)

# Establish a connection to Redis
redis_conn = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)


@celery.task(name="tasks.hello")
def hello():
    return "Hello from Celery!"


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
    redis_conn.set(redis_key, json.dumps(players))


@celery.task(name="tasks.pull_data")
def pull_data() -> None:
    for mode in MODES:
        for region in REGIONS:
            region_bool = region == "Takoroka"
            fetch_and_store_leaderboard_data(mode, region_bool)
