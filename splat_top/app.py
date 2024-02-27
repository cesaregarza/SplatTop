import datetime as dt

import sqlalchemy as db
from flask import Flask, jsonify, render_template, request
from flask_caching import Cache
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import scoped_session, sessionmaker

from splat_top.constants import MODES, REGIONS
from splat_top.db import create_uri
from splat_top.sql_types import Player, Schedule
from splat_top.utils import calculate_cache_refresh, get_seasons

app = Flask(__name__)
engine = db.create_engine(create_uri())
Session = scoped_session(sessionmaker(bind=engine))
cache = Cache(app, config={"CACHE_TYPE": "simple"})
jackpot_cache: tuple[dt.datetime, dict] = (dt.datetime(2023, 1, 1), {})


def cache_key():
    return f"{request.path}?{request.args}"


@app.route("/")
@cache.cached(timeout=60, key_prefix=cache_key)
def leaderboard():
    session = Session()

    mode = request.args.get("mode", "Splat Zones")
    region = request.args.get("region", "Tentatek")

    query = db.text(
        "SELECT p.* "
        "FROM xscraper.players p "
        "INNER JOIN ("
        "SELECT mode, MAX(timestamp) AS latest_timestamp "
        "FROM xscraper.players "
        "GROUP BY mode"
        ") AS latest ON p.mode = latest.mode "
        "AND p.timestamp = latest.latest_timestamp "
        "WHERE p.mode = :mode "
        "AND p.region = :region "
        "ORDER BY p.rank ASC;"
    )
    players = session.execute(
        query, {"mode": mode, "region": region}
    ).fetchall()
    players = [Player(**player._asdict()) for player in players]

    Session.remove()
    return render_template(
        "leaderboard.html",
        players=players,
        modes=MODES,
        regions=REGIONS,
        mode=mode,
        region=region,
    )


@app.route("/player/<string:player_id>")
def player_detail(player_id):
    session = Session()

    player = (
        session.query(Player)
        .filter_by(id=player_id)
        .order_by(Player.timestamp.desc())
        .first()
    )
    aliases = (
        session.query(
            func.concat(Player.name, "#", Player.name_id).label("alias"),
            func.max(Player.timestamp).label("last_seen"),
        )
        .filter(Player.id == player_id)
        .group_by("alias")
        .all()
    )
    aliases_data = [
        {
            "alias": alias[0],
            "last_seen": alias[1].strftime("%Y-%m-%d"),
        }
        for alias in aliases
        if alias[0] != f"{player.name}#{player.name_id}"
    ]
    # If no player found, return 404
    if player is None:
        return render_template("player_404.html"), 404
    peak_data = []

    modes_data = {}
    for mode in MODES:
        m_data = (
            session.query(
                Player.timestamp,
                Player.x_power,
                Schedule.stage_1_name,
                Schedule.stage_2_name,
                Player.weapon,
                Player.rank,
            )
            .join(
                Schedule,
                Schedule.start_time == Player.rotation_start,
                isouter=True,
            )
            .filter(Player.id == player_id, Player.mode == mode)
            .all()
        )
        modes_data[mode] = [
            {
                "timestamp": x[0].isoformat(),
                "x_power": x[1],
                "stage_1": x[2]
                if x[2] is not None
                else "Missing Schedule Data",
                "stage_2": x[3]
                if x[3] is not None
                else "Missing Schedule Data",
                "weapon": x[4],
                "rank": x[5],
            }
            for x in m_data
        ]

        # Get latest rank
        current_rank = (
            session.query(Player.rank, Player.weapon)
            .filter_by(id=player_id, mode=mode)
            .order_by(Player.timestamp.desc())
            .first()
        )
        if current_rank is None:
            continue
        current_rank, current_weapon = current_rank

        # Peak xpower
        peak_xpower = (
            session.query(Player.x_power, Player.timestamp)
            .filter_by(id=player_id, mode=mode)
            .order_by(Player.x_power.desc())
            .first()
        )

        # Peak rank
        peak_rank = (
            session.query(Player.rank, Player.timestamp)
            .filter_by(id=player_id, mode=mode)
            .order_by(Player.rank.asc(), Player.timestamp.asc())
            .first()
        )

        # Time since they reached current xpower
        current_xpower = (
            session.query(Player.x_power)
            .filter_by(id=player_id, mode=mode)
            .order_by(Player.timestamp.desc())
            .first()[0]
        )

        peak_data.append(
            {
                "peak_xpower": {
                    "x_power": peak_xpower[0],
                    "timestamp": peak_xpower[1].strftime("%Y-%m-%d"),
                },
                "peak_rank": {
                    "rank": peak_rank[0],
                    "timestamp": peak_rank[1].strftime("%Y-%m-%d"),
                },
                "mode": mode,
                "current": {
                    "x_power": current_xpower,
                    "rank": current_rank,
                    "weapon": current_weapon,
                },
            }
        )
        try:
            latest_timestamp = max(
                max(x["timestamp"] for x in mode_data)
                for mode_data in modes_data.values()
            )
            now_date = dt.datetime.fromisoformat(latest_timestamp)
        except ValueError:
            now_date = dt.datetime.now()

        seasons = get_seasons(now_date)

    Session.remove()

    return render_template(
        "player.html",
        player=player,
        modes_data=modes_data,
        aliases=aliases_data,
        peaks=peak_data,
        seasons=seasons,
    )


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/search")
def search_page():
    return render_template("search.html")


@app.route("/search_players", methods=["GET"])
def search_players():
    session = Session()
    query = request.args.get("q", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    if not query or len(query) < 3:
        return jsonify([])

    offset = (page - 1) * per_page

    raw_results = (
        session.query(Player)
        .filter(
            Player.search_text.ilike(f"%{query}%"),
        )
        .order_by(desc(Player.timestamp))
        .offset(offset)
        .limit(per_page)
        .all()
    )

    grouped_results = {}
    for player in raw_results:
        if player.id not in grouped_results:
            matched_alias = None
            if query.lower() in player.name.lower():
                matched_alias = player.name
            elif query.lower() in player.name_id.lower():
                matched_alias = player.name_id
            elif query.lower() in player.weapon.lower():
                matched_alias = player.weapon

            grouped_results[player.id] = {
                "player": player,
                "matched_alias": matched_alias,
            }

    Session.remove()

    return jsonify(
        [
            {
                "id": details["player"].id,
                "name": details["player"].name,
                "name_id": details["player"].name_id,
                "weapon": details["player"].weapon,
                "x_power": details["player"].x_power,
                "mode": details["player"].mode,
                "rank": details["player"].rank,
                "matched_alias": details["matched_alias"],
            }
            for details in grouped_results.values()
        ]
    )


@app.route("/jackpot")
def jackpot():
    now = dt.datetime.now()
    refresh_minutes = [6, 21, 36, 51]
    offset = 2
    jackpot_cache_time = jackpot_cache[0]
    stale = calculate_cache_refresh(
        reference_time=jackpot_cache_time,
        target_time=now,
        barriers=[x + offset for x in refresh_minutes],
        max_cache_time=60 * 15,
    )
    if not stale:
        return jsonify(jackpot_cache[1])

    session = Session()

    # Specify the player IDs you want to include in the jackpot
    player_map_id = {
        "Jared": "u-qlgolvdhwcwivrjbdnmm",
        "Leafi": "u-awyrn3umrfntlnxvlnmm",
        ".q": "u-qtpmoyyieljlmisvlnmm",
        "Madness": "u-ayz3jnyghvzbaaivlnmm",
    }
    reverse_player_map_id = {v: k for k, v in player_map_id.items()}

    player_ids = list(player_map_id.values())

    query = db.text(
        "SELECT * FROM xscraper.players "
        "WHERE id = ANY(:player_ids) "
        "AND (mode, timestamp) IN "
        "(SELECT mode, MAX(timestamp) FROM xscraper.players GROUP BY mode)"
    )

    # Fetch the players from the database
    players = session.execute(query, {"player_ids": player_ids}).fetchall()
    players = [Player(**player._asdict()) for player in players]

    Session.remove()

    # Prepare the data for the endpoint
    endpoint_data = {
        "players": [
            {
                "true_name": reverse_player_map_id[player.id],
                "id": player.id,
                "name": player.name,
                "name_id": player.name_id,
                "weapon": player.weapon,
                "x_power": player.x_power,
                "mode": player.mode,
                "rank": player.rank,
            }
            for player in players
        ]
    }

    jackpot_cache = (now, endpoint_data)

    return jsonify(endpoint_data)


if __name__ == "__main__":
    app.run(debug=True)
