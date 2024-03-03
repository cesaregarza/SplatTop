import datetime as dt

import sqlalchemy as db
from flask import Flask, jsonify, render_template, request
from flask_caching import Cache
from flask_cors import cross_origin
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
            Player.name,
            Player.name_id,
            func.max(Player.timestamp).label("last_seen"),
        )
        .filter(
            Player.id == player_id,
        )
        .group_by(Player.name, Player.name_id)
        .order_by(
            func.max(Player.timestamp).desc(),
        )
        .all()
    )
    aliases_data = [
        {
            "alias": f"{alias[0]}#{alias[1]}",
            "last_seen": alias[2].strftime("%Y-%m-%d"),
        }
        for alias in aliases
        if alias[0] != player.name
    ]
    # If no player found, return 404
    if player is None:
        return render_template("player_404.html"), 404
    peak_data = []

    all_modes_data = (
        session.query(
            Player.timestamp,
            Player.x_power,
            Schedule.stage_1_name,
            Schedule.stage_2_name,
            Player.weapon,
            Player.rank,
            Player.mode,
        )
        .join(
            Schedule,
            Schedule.start_time == Player.rotation_start,
            isouter=True,
        )
        .filter(Player.id == player_id)
        .all()
    )
    name_index_map = {
        "timestamp": 0,
        "x_power": 1,
        "stage_1": 2,
        "stage_2": 3,
        "weapon": 4,
        "rank": 5,
        "mode": 6,
    }
    modes_data = {}
    for mode in MODES:
        m_data = [
            x for x in all_modes_data if x[name_index_map["mode"]] == mode
        ]
        modes_data[mode] = [
            {
                "timestamp": x[name_index_map["timestamp"]].isoformat(),
                "x_power": x[name_index_map["x_power"]],
                "stage_1": x[name_index_map["stage_1"]]
                if x[name_index_map["stage_1"]] is not None
                else "Missing Schedule Data",
                "stage_2": x[name_index_map["stage_2"]]
                if x[name_index_map["stage_2"]] is not None
                else "Missing Schedule Data",
                "weapon": x[name_index_map["weapon"]],
                "rank": x[name_index_map["rank"]],
                "timestamp_raw": x[name_index_map["timestamp"]],
            }
            for x in m_data
        ]

        try:
            max_timestamp = max((x["timestamp"] for x in modes_data[mode]))
        except ValueError:
            continue
        peak_xpower = max(
            ((x["x_power"], x["timestamp_raw"]) for x in modes_data[mode]),
            key=lambda x: x[0],
        )
        current_rank, current_weapon, current_xpower = next(
            (
                x["rank"],
                x["weapon"],
                x["x_power"],
            )
            for x in modes_data[mode]
            if x["timestamp"] == max_timestamp
        )
        peak_rank = min(
            ((x["rank"], x["timestamp_raw"]) for x in modes_data[mode]),
            key=lambda x: x[0],
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
@cross_origin(origins="https://jackpot.splat.top")
def jackpot():
    global jackpot_cache
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
    player_extra_data = {
        "Jared": {
            "byname": "Stubborn Content Creator",
            "badges": [
                "QmFkZ2UtMTA1MDMwMQ==",
                "QmFkZ2UtMTA1MDEwMQ==",
                "QmFkZ2UtMTA1MDMxMQ==",
            ],
            "background_text_color": {"a": 1, "b": 0, "g": 0, "r": 0},
            "background_image": "TmFtZXBsYXRlQmFja2dyb3VuZC0xNTAzMg==",
        },
        "Leafi": {
            "byname": "Legendary Zipcaster User",
            "badges": [
                "QmFkZ2UtMTA4MDAwMQ==",
                "QmFkZ2UtMzAwMDEwMQ==",
                "QmFkZ2UtNTIyMDAwMg==",
            ],
            "background_text_color": {
                "a": 1,
                "b": 0.0235294104,
                "g": 0.0235294104,
                "r": 0.0352941193,
            },
            "background_image": "TmFtZXBsYXRlQmFja2dyb3VuZC04NjE=",
        },
        ".q": {
            "byname": "Classic Capriccioso",
            "badges": [
                "QmFkZ2UtNDEwMDExMA==",
                "QmFkZ2UtNDEwMDEyMA==",
                "QmFkZ2UtNDEwMDEwMA==",
            ],
            "background_text_color": {"a": 1, "b": 1, "g": 1, "r": 1},
            "background_image": "TmFtZXBsYXRlQmFja2dyb3VuZC0xNzAwMQ==",
        },
        "Madness": {
            "byname": "Assertive Stand-Up Comic",
            "badges": [
                "QmFkZ2UtNTAwMDAyMw==",
                "QmFkZ2UtNTIyMDAwMg==",
                "QmFkZ2UtMTA3MDEwMA==",
            ],
            "background_text_color": {
                "a": 1,
                "b": 0.321568608,
                "g": 0.129411802,
                "r": 0.0470588207,
            },
            "background_image": "TmFtZXBsYXRlQmFja2dyb3VuZC05MjQ=",
        },
    }

    player_ids = list(player_map_id.values())

    query = db.text(
        """
        (
            SELECT p.*
            FROM xscraper.players p
            INNER JOIN (
                SELECT mode, MAX(timestamp) AS max_timestamp
                FROM xscraper.players
                WHERE id = 'u-qlgolvdhwcwivrjbdnmm'
                GROUP BY mode
            ) AS LatestTimestamp
            ON p.mode = LatestTimestamp.mode
            AND p.timestamp = LatestTimestamp.max_timestamp
            WHERE p.id = 'u-qlgolvdhwcwivrjbdnmm'
        )
        UNION ALL
        (
            SELECT p.*
            FROM xscraper.players p
            INNER JOIN (
                SELECT mode, MAX(timestamp) AS max_timestamp
                FROM xscraper.players
                WHERE id = 'u-awyrn3umrfntlnxvlnmm'
                GROUP BY mode
            ) AS LatestTimestamp
            ON p.mode = LatestTimestamp.mode
            AND p.timestamp = LatestTimestamp.max_timestamp
            WHERE p.id = 'u-awyrn3umrfntlnxvlnmm'
        )
        UNION ALL
        (
            SELECT p.*
            FROM xscraper.players p
            INNER JOIN (
                SELECT mode, MAX(timestamp) AS max_timestamp
                FROM xscraper.players
                WHERE id = 'u-qtpmoyyieljlmisvlnmm'
                GROUP BY mode
            ) AS LatestTimestamp
            ON p.mode = LatestTimestamp.mode
            AND p.timestamp = LatestTimestamp.max_timestamp
            WHERE p.id = 'u-qtpmoyyieljlmisvlnmm'
        )
        UNION ALL
        (
            SELECT p.*
            FROM xscraper.players p
            INNER JOIN (
                SELECT mode, MAX(timestamp) AS max_timestamp
                FROM xscraper.players
                WHERE id = 'u-ayz3jnyghvzbaaivlnmm'
                GROUP BY mode
            ) AS LatestTimestamp
            ON p.mode = LatestTimestamp.mode
            AND p.timestamp = LatestTimestamp.max_timestamp
            WHERE p.id = 'u-ayz3jnyghvzbaaivlnmm'
        );
    """
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
                "weapon_id": player.weapon_id,
                "x_power": player.x_power,
                "mode": player.mode,
                "rank": player.rank,
                "byname": player_extra_data[reverse_player_map_id[player.id]][
                    "byname"
                ],
                "badges": player_extra_data[reverse_player_map_id[player.id]][
                    "badges"
                ],
                "background_text_color": player_extra_data[
                    reverse_player_map_id[player.id]
                ]["background_text_color"],
                "background_image": player_extra_data[
                    reverse_player_map_id[player.id]
                ]["background_image"],
            }
            for player in players
        ]
    }
    # Reformat the data from `players` to `mode`
    out = {}
    for player in endpoint_data["players"]:
        mode = player.pop("mode")
        if mode not in out:
            out[mode] = []
        out[mode].append(player)

    jackpot_cache = (now, out)
    return jsonify(out)


if __name__ == "__main__":
    app.run(debug=True)
