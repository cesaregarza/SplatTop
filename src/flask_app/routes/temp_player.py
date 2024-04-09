#### THIS FILE IS TEMPORARY JUST TO SERVE DATA TO THE FRONTEND FOR DEVELOPMENT ####
from flask import Blueprint, jsonify, render_template
from sqlalchemy import text

from flask_app.database import Session
from shared_lib.constants import MODES, REGIONS
from shared_lib.models import Player, PlayerLatest
from shared_lib.queries.player_queries import (
    PLAYER_ALIAS_QUERY,
    PLAYER_LATEST_QUERY,
    PLAYER_MOST_RECENT_ROW_QUERY,
)


def create_temp_player_bp() -> Blueprint:
    temp_player_bp = Blueprint("temp_player", __name__)

    @temp_player_bp.route("/player_test/<string:player_id>")
    def temp_player(player_id: str):
        base_query = """
        SELECT *
        FROM xscraper.players
        WHERE player_id = :player_id;
"""
        base_query = text(base_query)
        with Session() as session:
            result = session.execute(
                base_query, {"player_id": player_id}
            ).fetchall()
        # Turn the result into something JSON serializable
        result = [{**row._asdict()} for row in result]
        # Turn the datetime objects into strings
        for player in result:
            player["timestamp"] = player["timestamp"].isoformat()
            player["rotation_start"] = player["rotation_start"].isoformat()

        return jsonify(result)

    return temp_player_bp
