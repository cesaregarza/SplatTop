import asyncio
import json
import logging

from redis.client import PubSub

from fast_api_app.connections import connection_manager, redis_conn
from shared_lib.constants import PLAYER_PUBSUB_CHANNEL
from shared_lib.monitoring import (
    PUBSUB_ACTIVE,
    PUBSUB_BYTES_BROADCAST,
    PUBSUB_EVENTS,
    PUBSUB_RESTARTS,
    metrics_enabled,
)

logger = logging.getLogger(__name__)


async def process_pubsub_message(pubsub: PubSub):
    while True:
        message = pubsub.get_message()
        if message and message["type"] == "message":
            try:
                data = json.loads(message["data"])
            except json.JSONDecodeError:
                if metrics_enabled():
                    PUBSUB_EVENTS.labels(event="decode_error").inc()
                continue
            logger.info(f"Received player data for: {data['player_id']}")
            player_data = redis_conn.get(data["key"])
            if metrics_enabled():
                PUBSUB_EVENTS.labels(event="message").inc()
            if player_data is None:
                if metrics_enabled():
                    PUBSUB_EVENTS.labels(event="cache_miss").inc()
                continue
            if metrics_enabled():
                PUBSUB_BYTES_BROADCAST.labels(
                    player_id=data.get("player_id", "unknown")
                ).inc(len(player_data))
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
        if metrics_enabled():
            PUBSUB_RESTARTS.inc()
            PUBSUB_ACTIVE.set(1)

        try:
            await process_pubsub_message(pubsub)
        except Exception as e:
            logger.error(f"Error in pubsub listener: {e}")
            if metrics_enabled():
                PUBSUB_EVENTS.labels(event="listener_error").inc()
        finally:
            logger.info("Closing pubsub connection")
            pubsub.close()
            if metrics_enabled():
                PUBSUB_ACTIVE.set(0)


def start_pubsub_listener():
    logger.info("Starting pubsub listener")
    asyncio.create_task(listen_for_updates())
