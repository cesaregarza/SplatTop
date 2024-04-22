#### THIS FILE IS TEMPORARY JUST TO SERVE DATA TO THE FRONTEND FOR DEVELOPMENT ####
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import text

from flask_app.connections import async_session, celery, connection_manager
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
        player["latest_updated_timestamp"] = player[
            "latest_updated_timestamp"
        ].isoformat()

    logging.info("Returning initial player data")
    return result


@router.websocket("/ws/player/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    await connection_manager.connect(websocket, player_id)
    try:
        while True:
            data = await websocket.receive_text()
            await connection_manager.send_personal_message(
                f"You wrote: {data}", player_id
            )
    except WebSocketDisconnect:
        connection_manager.disconnect(player_id)
