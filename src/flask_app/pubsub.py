import json
import logging

from flask_app.connections import connection_manager, redis_conn
from shared_lib.constants import PLAYER_PUBSUB_CHANNEL


async def listen_for_updates():
    pubsub = redis_conn.pubsub()
    pubsub.subscribe(PLAYER_PUBSUB_CHANNEL)
    logging.info(f"Subscribed to channel: {PLAYER_PUBSUB_CHANNEL}")

    try:
        while True:
            message = pubsub.get_message()
            if message and message["type"] == "message":
                data = json.loads(message["data"])
                logging.info(f"Received player data for: {data['player_id']}")
                await connection_manager.broadcast(json.dumps(data))
    except Exception as e:
        logging.error(f"Error in pubsub listener: {e}")
    finally:
        pubsub.close()
