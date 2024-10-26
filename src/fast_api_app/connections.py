import asyncio
import logging
import sqlite3
import zlib

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
from shared_lib.db import create_uri

# Setup logger
logger = logging.getLogger(__name__)

# Create both synchronous and asynchronous engines
sync_engine = create_engine(create_uri())
async_engine = create_async_engine(create_uri())

# Synchronous session
Session = scoped_session(sessionmaker(bind=sync_engine))

# Asynchronous session with pool
async_session_factory = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)
async_session = scoped_session(async_session_factory)

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

    async def broadcast(self, message: str):
        for player_id in self.active_connections:
            for connection_id in self.active_connections[player_id]:
                await self.active_connections[player_id][
                    connection_id
                ].send_text(message)

    async def broadcast_player_data(self, message: str, player_id: str):
        logger.info("Broadcasting player data for: %s", player_id)
        if player_id in self.active_connections:
            compressed_message = zlib.compress(message.encode())
            logger.info("Player is connected, sending compressed data")
            logger.info(
                "Original message length: %s, Compressed message length: %s",
                f"{len(message):,}",
                f"{len(compressed_message):,}",
            )
            for connection_id in self.active_connections[player_id]:
                await self.active_connections[player_id][
                    connection_id
                ].send_bytes(compressed_message)
            logger.info("Compressed data sent")
        else:
            logger.info("Player %s not connected", player_id)


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

    async def process_queue(self):
        if self.processing:
            return

        self.processing = True
        try:
            while True:
                request, future = await self.queue.get()
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
                finally:
                    self.queue.task_done()

                if self.queue.empty():
                    break
        finally:
            self.processing = False

    async def add_to_queue(self, request: dict) -> dict:
        future = asyncio.Future()
        await self.queue.put((request, future))
        asyncio.create_task(self.process_queue())
        return await future


model_queue = ModelQueue()
