import logging
import sqlite3

import redis
from celery import Celery
from fastapi import WebSocket
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from shared_lib.constants import REDIS_HOST, REDIS_PORT
from shared_lib.db import create_uri

# Setup logger
logger = logging.getLogger(__name__)

# Create both synchronous and asynchronous engines
sync_engine = create_engine(create_uri())
async_engine = create_async_engine(create_uri())

# Synchronous session
Session = scoped_session(sessionmaker(bind=sync_engine))

# Asynchronous session
async_session = scoped_session(
    sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
)

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
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, player_id: str):
        await websocket.accept()
        self.active_connections[player_id] = websocket
        logger.info(f"Client connected and added to room: {player_id}")
        celery.send_task("tasks.fetch_player_data", args=[player_id])
        logger.info("Task sent to Celery")

    def disconnect(self, player_id: str):
        if player_id in self.active_connections:
            del self.active_connections[player_id]
            logger.info("Client disconnected, id: %s", player_id)

    async def send_personal_message(self, message: str, player_id: str):
        if player_id in self.active_connections:
            await self.active_connections[player_id].send_text(message)

    async def broadcast(self, message: str):
        for player_id in self.active_connections:
            await self.active_connections[player_id].send_text(message)

    async def broadcast_player_data(self, message: str, player_id: str):
        logger.info(f"Broadcasting player data for: {player_id}")
        if player_id in self.active_connections:
            logger.info("Player is connected, sending data")
            logger.info(f"Message length: {len(message):,}")
            await self.active_connections[player_id].send_text(message)
            logger.info("Data sent")
        else:
            logger.info(f"Player {player_id} not connected")


connection_manager = ConnectionManager()

# Create the SQLite database in memory
sqlite_conn = sqlite3.connect(":memory:")
sqlite_cursor = sqlite_conn.cursor()
