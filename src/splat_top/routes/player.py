from flask import render_template
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from splat_top.app import app, Session as ScopedSession, get_seasons
from splat_top.constants import MODES
from splat_top.sql_types import Player, Schedule

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