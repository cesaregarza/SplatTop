from flask import Blueprint, jsonify, render_template, request
from flask_caching import Cache
from sqlalchemy import text

from flask_app.database import Session
from shared_lib.constants import MODES, REGIONS
from shared_lib.models import Player
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

        return jsonify(
            {
                "players": players,
                "modes": MODES,
                "regions": REGIONS,
                "mode": mode,
            }
        )

    return front_page_bp
