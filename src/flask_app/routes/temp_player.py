#### THIS FILE IS TEMPORARY JUST TO SERVE DATA TO THE FRONTEND FOR DEVELOPMENT ####
import logging
from fastapi import APIRouter, WebSocket, HTTPException, WebSocketDisconnect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from flask_app.connections import async_session, celery
from shared_lib.queries.player_queries import PLAYER_ALIAS_QUERY

router = APIRouter()

@router.get("/player_test/{player_id}")
async def temp_player(player_id: str):
    # Send a task to Celery and immediately return initial data
    logging.info(f"Fetching player data for: {player_id}")
    celery.send_task("tasks.fetch_player_data", args=[player_id])
    logging.info("Task sent to Celery")
    
    async with async_session() as session:  # Ensure you have an asynchronous session
        logging.info("Fetching initial player data")
        result = await session.execute(
            text(PLAYER_ALIAS_QUERY), {"player_id": player_id}
        )
        result = result.fetchall()

    logging.info("Initial player data fetched")
    result = [{**row._asdict()} for row in result]
    for player in result:
        player["latest_updated_timestamp"] = player["latest_updated_timestamp"].isoformat()

    logging.info("Returning initial player data")
    return result

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, player_id: str):
        await websocket.accept()
        self.active_connections[player_id] = websocket
        logging.info(f"Client connected and added to room: {player_id}")

    def disconnect(self, player_id: str):
        if player_id in self.active_connections:
            del self.active_connections[player_id]
            logging.info("Client disconnected")

    async def send_personal_message(self, message: str, player_id: str):
        if player_id in self.active_connections:
            await self.active_connections[player_id].send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/player/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    await manager.connect(websocket, player_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", player_id)
    except WebSocketDisconnect:
        manager.disconnect(player_id)
