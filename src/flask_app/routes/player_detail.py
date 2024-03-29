from flask import Blueprint, render_template, request
from flask_caching import Cache
from sqlalchemy import text

from flask_app.database import Session
from shared_lib.constants import MODES, REGIONS
from shared_lib.models import Player, PlayerLatest
from shared_lib.queries import (
    PLAYER_ALIAS_QUERY,
    PLAYER_LATEST_QUERY,
    PLAYER_MOST_RECENT_ROW_QUERY,
)


def create_player_detail_bp() -> Blueprint:
    player_detail_bp = Blueprint("player_detail", __name__)

    @player_detail_bp.route("/player/<string:player_id>")
    def player_detail(player_id: str):
        base_query = text(PLAYER_LATEST_QUERY)
        with Session() as session:
            result = session.execute(
                base_query, {"player_id": player_id}
            ).fetchall()

            if not result:
                return render_template("player_404.html"), 404

            aliases = session.execute(
                text(PLAYER_ALIAS_QUERY), {"player_id": player_id}
            ).fetchall()

            player = session.execute(
                text(PLAYER_MOST_RECENT_ROW_QUERY), {"player_id": player_id}
            ).fetchone()

        latest_data = [PlayerLatest(**player._asdict()) for player in result]
        aliases_data = [
            {
                "alias": alias[0],
                "last_updated": alias[1].strftime("%Y-%m-%d"),
            }
            for alias in aliases
        ]
        # Sort the aliases so the most recent is first
        aliases_data.sort(key=lambda x: x["last_updated"], reverse=True)

        return render_template(
            "player_dev.html",
            player_details=player,
            data={},
            aliases=aliases_data,
            modes=MODES,
        )
    
    return player_detail_bp
