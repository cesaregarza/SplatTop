#### THIS FILE IS TEMPORARY JUST TO SERVE DATA TO THE FRONTEND FOR DEVELOPMENT ####
import logging

from flask import Blueprint, jsonify, request
from flask_socketio import SocketIO, join_room
from sqlalchemy import text

from flask_app.connections import Session, celery
from shared_lib.queries.player_queries import PLAYER_ALIAS_QUERY


def create_temp_player_bp(socketio: SocketIO) -> Blueprint:
    temp_player_bp = Blueprint("temp_player", __name__)

    @temp_player_bp.route("/player_test/<string:player_id>")
    def temp_player(player_id: str):
        # Send a task to Celery and immediately return initial data
        logging.info(f"Fetching player data for: {player_id}")
        celery.send_task("tasks.fetch_player_data", args=[player_id])
        logging.info("Task sent to Celery")
        with Session() as session:
            logging.info("Fetching initial player data")
            result = session.execute(
                text(PLAYER_ALIAS_QUERY), {"player_id": player_id}
            ).fetchall()
        
        logging.info("Initial player data fetched")
        result = [{**row._asdict()} for row in result]
        for player in result:
            player["latest_updated_timestamp"] = player["latest_updated_timestamp"].isoformat()

        logging.info("Returning initial player data")
        return jsonify(result)

    @socketio.on("connect", namespace="/player")
    def handle_connect():
        # Obtain player_id from the query string during WebSocket connection
        player_id = request.args.get("player_id")
        if player_id:
            join_room(player_id)
            logging.info(f"Client connected and added to room: {player_id}")
        else:
            logging.error("Failed to connect: player_id is missing")
            return False  # Disconnect the client if player_id is not provided

    @socketio.on("disconnect", namespace="/player")
    def handle_disconnect():
        logging.info("Client disconnected")

    return temp_player_bp
