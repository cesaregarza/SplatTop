from flask import render_template, request
from sqlalchemy import text

from splat_top.constants import MODES, REGIONS
from splat_top.sql_types import Player
from splat_top.app import app, Session, cache


def cache_key():
    return f"{request.path}?{request.args}"


@app.route("/")
@cache.cached(timeout=60, key_prefix=cache_key)
def leaderboard():

    mode = request.args.get("mode", "Splat Zones")
    region = request.args.get("region", "Tentatek") 

    query = text(
        "WITH MaxTimestamp AS ("
        "SELECT MAX(timestamp) AS max_timestamp "
        "FROM xscraper.players "
        "WHERE mode = :mode "
        "), "
        "FilteredByTimestamp AS ("
        "SELECT * "
        "FROM xscraper.players "
        "WHERE timestamp = (SELECT max_timestamp FROM MaxTimestamp) "
        ") "
        "SELECT * "
        "FROM FilteredByTimestamp "
        "WHERE mode = :mode "
        "AND region = :region "
        "ORDER BY rank ASC;"
    )

    with Session() as session:
        result = session.execute(
            query, {"mode": mode, "region": region}
        ).fetchall()
        players = [Player(**player._asdict()) for player in result]

    return render_template(
        "leaderboard.html",
        players=players,
        modes=MODES,
        regions=REGIONS,
        mode=mode,
        region=region,
    )

