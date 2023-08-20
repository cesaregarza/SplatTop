import sqlalchemy as db
from flask import Flask, render_template, request
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from splat_top.db import create_uri
from splat_top.sql_types import Player
from splat_top.constants import MODES, REGIONS

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
    return render_template("leaderboard.html", players=players, modes=MODES, regions=REGIONS)


@app.route('/player/<string:player_id>')
def player_detail(player_id):
    Session = sessionmaker(bind=engine)
    session = Session()

    player = session.query(Player).filter_by(id=player_id).first()
    modes_data = {}
    for mode in MODES:
        data = session.query(Player.timestamp, Player.x_power).filter_by(id=player_id, mode=mode).all()
        modes_data[mode] = [(x[0].isoformat(), x[1]) for x in data]

    session.close()

    return render_template('player.html', player=player, modes_data=modes_data)



if __name__ == "__main__":
    app.run(debug=True)
