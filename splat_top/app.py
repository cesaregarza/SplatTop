import sqlalchemy as db
from flask import Flask, render_template, request
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from splat_top.constants import MODES, REGIONS
from splat_top.db import create_uri
from splat_top.sql_types import Player

app = Flask(__name__)
engine = db.create_engine(create_uri())


@app.route("/")
def leaderboard():
    Session = sessionmaker(bind=engine)
    session = Session()

    mode = request.args.get("mode", "Splat Zones")
    region = request.args.get("region", "Tentatek")

    subquery = (
        session.query(
            Player.mode, func.max(Player.timestamp).label("latest_timestamp")
        )
        .group_by(Player.mode)
        .subquery()
    )

    players = (
        session.query(Player)
        .join(
            subquery,
            (subquery.c.latest_timestamp == Player.timestamp)
            & (subquery.c.mode == Player.mode),
        )
        .filter(Player.mode == mode)
        .filter(Player.region == region)
        .order_by(Player.mode.asc())
        .order_by(Player.region.asc())
        .order_by(Player.rank.asc())
        .all()
    )

    session.close()
    return render_template(
        "leaderboard.html", players=players, modes=MODES, regions=REGIONS
    )


@app.route("/player/<string:player_id>")
def player_detail(player_id):
    Session = sessionmaker(bind=engine)
    session = Session()

    player = session.query(Player).filter_by(id=player_id).first()
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
    peak_data = []
    rank_data = []
    modes_data = {}
    for mode in MODES:
        m_data = (
            session.query(Player.timestamp, Player.x_power)
            .filter_by(id=player_id, mode=mode)
            .all()
        )
        modes_data[mode] = [(x[0].isoformat(), x[1]) for x in m_data]

        # Get latest rank
        rank_data.append(
            {
                "rank": (
                    session.query(Player.rank)
                    .filter_by(id=player_id, mode=mode)
                    .order_by(Player.timestamp.desc())
                    .first()[0]
                ),
                "mode": mode,
            }
        )

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
            .order_by(Player.rank.desc())
            .first()
        )

        # Time since they reached current xpower
        last_played_time = (
            session.query(Player.timestamp)
            .filter_by(id=player_id, mode=mode, x_power=player.x_power)
            .order_by(Player.timestamp.desc())
            .first()
        )

        peak_data.append(
            {
                "peak_xpower": peak_xpower,
                "peak_rank": peak_rank,
                "last_played_time": last_played_time,
            }
        )

    session.close()

    return render_template(
        "player.html",
        player=player,
        modes_data=modes_data,
        aliases=aliases_data,
        peak_data=peak_data,
        ranks=rank_data,
    )


if __name__ == "__main__":
    app.run(debug=True)
