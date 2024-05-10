import asyncio
import json
import logging

from redis.client import PubSub

from fast_api_app.connections import connection_manager, redis_conn
from shared_lib.constants import PLAYER_PUBSUB_CHANNEL

logger = logging.getLogger(__name__)


async def process_pubsub_message(pubsub: PubSub):
    while True:
        message = pubsub.get_message()
        if message and message["type"] == "message":
            data = json.loads(message["data"])
            logger.info(f"Received player data for: {data['player_id']}")
            player_data = redis_conn.get(data["key"])
            await connection_manager.broadcast_player_data(
                player_data, data["player_id"]
            )
        else:
            await asyncio.sleep(0.01)


async def listen_for_updates():
    while True:
        pubsub = redis_conn.pubsub()
        pubsub.subscribe(PLAYER_PUBSUB_CHANNEL)
        logger.info(f"Subscribed to channel: {PLAYER_PUBSUB_CHANNEL}")

        try:
            await process_pubsub_message(pubsub)
        except Exception as e:
            logger.error(f"Error in pubsub listener: {e}")
        finally:
            logger.info("Closing pubsub connection")
            pubsub.close()


def start_pubsub_listener():
    logger.info("Starting pubsub listener")
    asyncio.create_task(listen_for_updates())
