from flask import Blueprint, jsonify, request
from flask_caching import Cache
from sqlalchemy import text

from flask_app.database import Session
from flask_app.utils import get_badge_image, get_banner_image, get_weapon_image
from shared_lib.queries import LEADERBOARD_MAIN_QUERY


def cache_key():
    return f"{request.path}?{request.args}"


def create_front_page_bp(cache: Cache) -> Blueprint:
    front_page_bp = Blueprint("front_page", __name__)

    @front_page_bp.route("/api/leaderboard")
    @cache.cached(timeout=60, key_prefix=cache_key)
    def leaderboard():
        mode = request.args.get("mode", "Splat Zones")
        region = request.args.get("region", "Tentatek")
        region_bool = region == "Takoroka"

        query = text(LEADERBOARD_MAIN_QUERY)

        with Session() as session:
            result = session.execute(
                query, {"mode": mode, "region": region_bool}
            ).fetchall()
            # players = [Player(**player._asdict()) for player in result]
            players = [{**row._asdict()} for row in result]

        # Replace weapon_id, badge_id, and banner_id with images
        for player in players:
            player["weapon_image"] = get_weapon_image(int(player["weapon_id"]))
            player["badge_left_image"] = get_badge_image(
                player["badge_left_id"]
            )
            player["badge_center_image"] = get_badge_image(
                player["badge_center_id"]
            )
            player["badge_right_image"] = get_badge_image(
                player["badge_right_id"]
            )
            player["nameplate_image"] = get_banner_image(
                int(player["nameplate_id"])
            )

        return jsonify(
            {
                "players": players,
            }
        )

    return front_page_bp
