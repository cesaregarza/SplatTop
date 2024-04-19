import json
import logging

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from flask_app.connections import redis_conn
from shared_lib.constants import PLAYER_PUBSUB_CHANNEL

async def listen_for_updates(websocket: WebSocket):
    pubsub = redis_conn.pubsub()
    pubsub.subscribe(PLAYER_PUBSUB_CHANNEL)

    await websocket.accept()
    try:
        while True:
            message = pubsub.get_message()
            if message and message["type"] == "message":
                data = json.loads(message["data"])
                logging.info(f"Received player data for: {data['player_id']}")
                await websocket.send_json(data)
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
    finally:
        pubsub.close()
        await websocket.close()