import json

import redis
from flask import Blueprint, jsonify, request

redis_conn = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)


def create_front_page_bp() -> Blueprint:
    front_page_bp = Blueprint("front_page", __name__)

    @front_page_bp.route("/api/leaderboard")
    def leaderboard():
        mode = request.args.get("mode", "Splat Zones")
        region = request.args.get("region", "Tentatek")
        region_bool = "Takoroka" if region == "Takoroka" else "Tentatek"

        redis_key = f"leaderboard_data:{mode}:{region_bool}"
        players = redis_conn.get(redis_key)

        if players is None:
            return (
                jsonify({"error": "Data is not available yet, please wait."}),
                503,
            )
        else:
            players = json.loads(players)
            return jsonify({"players": players})

    return front_page_bp
