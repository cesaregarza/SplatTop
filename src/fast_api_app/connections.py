import asyncio
import logging
import sqlite3
import zlib
from time import perf_counter

import httpx
import redis
from celery import Celery
from fastapi import WebSocket
from slowapi import Limiter
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from fast_api_app.utils import get_client_ip
from shared_lib.constants import REDIS_HOST, REDIS_PORT
from shared_lib.db import create_ranking_uri, create_uri
from shared_lib.monitoring import (
    SPLATGPT_ERRORS,
    SPLATGPT_INFLIGHT,
    SPLATGPT_QUEUE_SIZE,
    WEBSOCKET_BROADCAST_DURATION,
    WEBSOCKET_BYTES_SENT,
    WEBSOCKET_CONNECTIONS,
    WEBSOCKET_EVENTS,
    metrics_enabled,
)

# Setup logger
logger = logging.getLogger(__name__)

# Create both synchronous and asynchronous engines
sync_engine = create_engine(create_uri())
async_engine = create_async_engine(create_uri())

# Separate rankings async engine/session for ripple endpoints
rankings_async_engine = create_async_engine(create_ranking_uri())

# Synchronous session
Session = scoped_session(sessionmaker(bind=sync_engine))

# Asynchronous session with pool
async_session_factory = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)
async_session = scoped_session(async_session_factory)

rankings_async_session_factory = sessionmaker(
    bind=rankings_async_engine, class_=AsyncSession, expire_on_commit=False
)
rankings_async_session = scoped_session(rankings_async_session_factory)

REDIS_URI = f"redis://{REDIS_HOST}:{REDIS_PORT}"
celery = Celery("tasks", broker=REDIS_URI, backend=REDIS_URI)

pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
    max_connections=10,
)
redis_conn = redis.Redis(connection_pool=pool)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, dict[str, WebSocket]] = {}
        self.heartbeat_interval = 30

    async def connect(
        self, websocket: WebSocket, player_id: str, connection_id: str
    ):
        await websocket.accept()
        if player_id not in self.active_connections:
            self.active_connections[player_id] = {}
        self.active_connections[player_id][connection_id] = websocket
        if metrics_enabled():
            WEBSOCKET_EVENTS.labels(event="connected").inc()
            WEBSOCKET_CONNECTIONS.labels(player_id=player_id).set(
                len(self.active_connections[player_id])
            )
        logger.info(
            "Client connected and added to room: %s with connection id: %s",
            player_id,
            connection_id,
        )
        celery.send_task("tasks.fetch_player_data", args=[player_id])
        logger.info("Task sent to Celery")

    def disconnect(self, player_id: str, connection_id: str):
        if (
            player_id in self.active_connections
            and connection_id in self.active_connections[player_id]
        ):
            del self.active_connections[player_id][connection_id]
            if not self.active_connections[player_id]:
                del self.active_connections[player_id]
                if metrics_enabled():
                    try:
                        WEBSOCKET_CONNECTIONS.remove(player_id)
                    except KeyError:
                        pass
            elif metrics_enabled():
                WEBSOCKET_CONNECTIONS.labels(player_id=player_id).set(
                    len(self.active_connections[player_id])
                )
            if metrics_enabled():
                WEBSOCKET_EVENTS.labels(event="disconnected").inc()
            logger.info(
                "Client disconnected, id: %s, connection id: %s",
                player_id,
                connection_id,
            )

    async def send_personal_message(
        self, message: str, player_id: str, connection_id: str
    ):
        if (
            player_id in self.active_connections
            and connection_id in self.active_connections[player_id]
        ):
            await self.active_connections[player_id][connection_id].send_text(
                message
            )
            if metrics_enabled():
                WEBSOCKET_EVENTS.labels(event="personal_message").inc()

    async def broadcast(self, message: str):
        for player_id in self.active_connections:
            for connection_id in self.active_connections[player_id]:
                await self.active_connections[player_id][
                    connection_id
                ].send_text(message)
                if metrics_enabled():
                    WEBSOCKET_EVENTS.labels(event="broadcast_message").inc()

    async def broadcast_player_data(self, message: str, player_id: str):
        logger.info("Broadcasting player data for: %s", player_id)
        if player_id in self.active_connections:
            start = perf_counter()
            compressed_message = zlib.compress(message.encode())
            logger.info("Player is connected, sending compressed data")
            logger.info(
                "Original message length: %s, Compressed message length: %s",
                f"{len(message):,}",
                f"{len(compressed_message):,}",
            )
            recipients = len(self.active_connections[player_id])
            for connection_id in self.active_connections[player_id]:
                await self.active_connections[player_id][
                    connection_id
                ].send_bytes(compressed_message)
            if metrics_enabled():
                duration = perf_counter() - start
                WEBSOCKET_EVENTS.labels(event="broadcast").inc(recipients)
                WEBSOCKET_BROADCAST_DURATION.labels(player_id=player_id).observe(
                    duration
                )
                WEBSOCKET_BYTES_SENT.labels(player_id=player_id).inc(
                    len(compressed_message) * recipients
                )
            logger.info("Compressed data sent")
        else:
            logger.info("Player %s not connected", player_id)
            if metrics_enabled():
                WEBSOCKET_EVENTS.labels(event="broadcast_dropped").inc()


connection_manager = ConnectionManager()

# Create the SQLite database in memory
sqlite_conn = sqlite3.connect(":memory:")
sqlite_cursor = sqlite_conn.cursor()

# Create slowapi limiter
limiter = Limiter(key_func=get_client_ip)


# Model Queue for SplatGPT
class ModelQueue:
    def __init__(self, cache_expiration: int = 60 * 10):
        self.queue = asyncio.Queue()
        self.processing = False
        self.client = httpx.AsyncClient()
        self.cache_key_prefix = "splatgpt"
        self.cache_expiration = cache_expiration
        if metrics_enabled():
            SPLATGPT_QUEUE_SIZE.set(0)
            SPLATGPT_INFLIGHT.set(0)

    async def process_queue(self):
        if self.processing:
            return

        self.processing = True
        try:
            while True:
                request, future = await self.queue.get()
                if metrics_enabled():
                    SPLATGPT_QUEUE_SIZE.set(self.queue.qsize())
                    SPLATGPT_INFLIGHT.inc()
                try:
                    response = await self.client.post(
                        "http://splatnlp-service:9000/infer",
                        json=request,
                    )
                    response.raise_for_status()
                    result = response.json()
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                    if metrics_enabled():
                        SPLATGPT_ERRORS.labels(stage="model_http").inc()
                finally:
                    self.queue.task_done()
                    if metrics_enabled():
                        SPLATGPT_INFLIGHT.dec()

                if self.queue.empty():
                    break
        finally:
            if metrics_enabled():
                SPLATGPT_QUEUE_SIZE.set(self.queue.qsize())
            self.processing = False

    async def add_to_queue(self, request: dict) -> dict:
        future = asyncio.Future()
        await self.queue.put((request, future))
        if metrics_enabled():
            SPLATGPT_QUEUE_SIZE.set(self.queue.qsize())
        asyncio.create_task(self.process_queue())
        return await future


model_queue = ModelQueue()
