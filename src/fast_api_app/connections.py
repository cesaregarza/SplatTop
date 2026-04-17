import asyncio
import logging
import sqlite3
import zlib
from time import perf_counter

import httpx
import orjson
import redis
from celery import Celery
from fastapi import WebSocket
from slowapi import Limiter
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import scoped_session, sessionmaker

from fast_api_app.utils import get_client_ip
from shared_lib.constants import PLAYER_LATEST_REDIS_KEY, REDIS_HOST, REDIS_PORT
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
# Version 2 streams player detail state as snapshot, analysis, then complete.
PLAYER_CHUNK_VERSION = 2
PLAYER_AGGREGATED_KEYS = (
    "weapon_counts",
    "weapon_winrate",
    "season_results",
    "aggregate_season_data",
    "latest_data",
)

# Create both synchronous and asynchronous engines
sync_engine = create_engine(create_uri())
async_engine = create_async_engine(create_uri())

# Separate rankings async engine/session for ripple endpoints
rankings_async_engine = create_async_engine(create_ranking_uri())

# Synchronous session
Session = scoped_session(sessionmaker(bind=sync_engine))

# Asynchronous session with pool
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
async_session = async_session_factory

rankings_async_session = async_sessionmaker(
    rankings_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
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
        self.active_connections: dict[str, dict[str, dict]] = {}
        self.heartbeat_interval = 30

    async def connect(
        self,
        websocket: WebSocket,
        player_id: str,
        connection_id: str,
        *,
        progressive: bool = False,
    ):
        await websocket.accept()
        if player_id not in self.active_connections:
            self.active_connections[player_id] = {}
        self.active_connections[player_id][connection_id] = {
            "websocket": websocket,
            "progressive": progressive,
        }
        if metrics_enabled():
            WEBSOCKET_EVENTS.labels(event="connected").inc()
            WEBSOCKET_CONNECTIONS.labels(player_id=player_id).set(
                len(self.active_connections[player_id])
            )
        logger.info(
            "Client connected and added to room: %s with connection id: %s (progressive=%s)",
            player_id,
            connection_id,
            progressive,
        )
        cache_key = f"{PLAYER_LATEST_REDIS_KEY}:{player_id}"
        cached_payload_raw = redis_conn.get(cache_key)
        if cached_payload_raw is not None:
            try:
                await self.send_cached_player_payload(
                    websocket,
                    player_id,
                    cached_payload_raw,
                    cache_key,
                    progressive=progressive,
                )
                logger.info("Cached player data sent directly")
                return
            except Exception:
                logger.exception(
                    "Failed to send cached player data directly for %s",
                    player_id,
                )
        celery.send_task("tasks.fetch_player_data", args=[player_id])
        logger.info("Task sent to Celery")

    @staticmethod
    def _build_empty_player_payload() -> dict:
        return {
            "player_data": [],
            "aggregated_data": {
                key: [] for key in PLAYER_AGGREGATED_KEYS
            },
        }

    @classmethod
    def _merge_player_payload(
        cls, payload: dict | None
    ) -> dict:
        merged_payload = cls._build_empty_player_payload()
        if payload is None:
            return merged_payload
        if "player_data" in payload and payload["player_data"] is not None:
            merged_payload["player_data"] = payload["player_data"]
        aggregated_payload = payload.get("aggregated_data") or {}
        for key in PLAYER_AGGREGATED_KEYS:
            if key in aggregated_payload and aggregated_payload[key] is not None:
                merged_payload["aggregated_data"][key] = aggregated_payload[key]
        return merged_payload

    @classmethod
    def _build_cached_snapshot_payload(cls, payload: dict) -> dict:
        aggregated_payload = payload.get("aggregated_data") or {}
        return {
            "aggregated_data": {
                "season_results": aggregated_payload.get("season_results", []),
                "latest_data": aggregated_payload.get("latest_data", []),
            }
        }

    @classmethod
    def _build_cached_analysis_payload(cls, payload: dict) -> dict:
        aggregated_payload = payload.get("aggregated_data") or {}
        return {
            "player_data": payload.get("player_data", []),
            "aggregated_data": {
                "aggregate_season_data": aggregated_payload.get(
                    "aggregate_season_data", []
                ),
                "weapon_counts": aggregated_payload.get("weapon_counts", []),
                "weapon_winrate": aggregated_payload.get(
                    "weapon_winrate", []
                ),
            },
        }

    @staticmethod
    async def _send_compressed_message(
        websocket: WebSocket, message: str | bytes
    ) -> None:
        message_bytes = (
            message.encode() if isinstance(message, str) else message
        )
        await websocket.send_bytes(zlib.compress(message_bytes))

    async def send_cached_player_payload(
        self,
        websocket: WebSocket,
        player_id: str,
        cached_payload_raw: str | bytes,
        cache_key: str,
        *,
        progressive: bool,
    ) -> None:
        cached_payload_bytes = (
            cached_payload_raw.encode()
            if isinstance(cached_payload_raw, str)
            else cached_payload_raw
        )
        if progressive:
            cached_payload = self._merge_player_payload(
                orjson.loads(cached_payload_bytes)
            )
            messages = [
                {
                    "player_id": player_id,
                    "type": "player_chunk",
                    "version": PLAYER_CHUNK_VERSION,
                    "phase": "snapshot",
                    "payload": self._build_cached_snapshot_payload(
                        cached_payload
                    ),
                },
                {
                    "player_id": player_id,
                    "type": "player_chunk",
                    "version": PLAYER_CHUNK_VERSION,
                    "phase": "analysis",
                    "payload": self._build_cached_analysis_payload(
                        cached_payload
                    ),
                },
                {
                    "player_id": player_id,
                    "type": "player_chunk",
                    "version": PLAYER_CHUNK_VERSION,
                    "phase": "complete",
                    "payload": {},
                    "key": cache_key,
                },
            ]
            for message in messages:
                await self._send_compressed_message(
                    websocket, orjson.dumps(message)
                )
            return

        await self._send_compressed_message(websocket, cached_payload_bytes)

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
            websocket = self.active_connections[player_id][connection_id][
                "websocket"
            ]
            await websocket.send_text(message)
            if metrics_enabled():
                WEBSOCKET_EVENTS.labels(event="personal_message").inc()

    async def broadcast(self, message: str):
        for player_id in self.active_connections:
            for connection_id in self.active_connections[player_id]:
                websocket = self.active_connections[player_id][connection_id][
                    "websocket"
                ]
                await websocket.send_text(message)
                if metrics_enabled():
                    WEBSOCKET_EVENTS.labels(event="broadcast_message").inc()

    async def broadcast_player_data(
        self,
        message: str | bytes,
        player_id: str,
        *,
        progressive_only: bool = False,
        legacy_only: bool = False,
    ):
        logger.info("Broadcasting player data for: %s", player_id)
        if player_id in self.active_connections:
            start = perf_counter()
            message_bytes = (
                message.encode() if isinstance(message, str) else message
            )
            compressed_message = zlib.compress(message_bytes)
            logger.info("Player is connected, sending compressed data")
            logger.info(
                "Original message length: %s, Compressed message length: %s",
                f"{len(message_bytes):,}",
                f"{len(compressed_message):,}",
            )
            recipients = 0
            for connection_id in self.active_connections[player_id]:
                connection = self.active_connections[player_id][connection_id]
                if progressive_only and not connection["progressive"]:
                    continue
                if legacy_only and connection["progressive"]:
                    continue
                await connection["websocket"].send_bytes(compressed_message)
                recipients += 1
            if recipients == 0:
                logger.info(
                    "No matching websocket recipients for player %s",
                    player_id,
                )
                return
            if metrics_enabled():
                duration = perf_counter() - start
                WEBSOCKET_EVENTS.labels(event="broadcast").inc(recipients)
                WEBSOCKET_BROADCAST_DURATION.labels(
                    player_id=player_id
                ).observe(duration)
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
