import json
import logging

from flask_socketio import SocketIO

from flask_app.connections import redis_conn
from flask_app.socketio_constants.events import PLAYER_DATA_EVENT
from flask_app.socketio_constants.namespaces import PLAYER_DATA_NAMESPACE
from shared_lib.constants import PLAYER_PUBSUB_CHANNEL


def listen_for_updates(socketio: SocketIO) -> None:
    pubsub = redis_conn.pubsub()
    pubsub.subscribe(PLAYER_PUBSUB_CHANNEL)

    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            logging.info(f"Received player data for: {data['player_id']}")
            player_id = data["player_id"]
            socketio.emit(
                PLAYER_DATA_EVENT,
                data["data"],
                room=player_id,
                namespace=PLAYER_DATA_NAMESPACE,
            )
