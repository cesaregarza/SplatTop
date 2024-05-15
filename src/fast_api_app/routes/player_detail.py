import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import text

from fast_api_app.connections import async_session_factory, connection_manager
from shared_lib.queries.player_queries import PLAYER_ALIAS_QUERY

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/api/player/{player_id}")
async def player_detail(player_id: str):
    async with async_session_factory() as session:
        logger.info("Fetching initial player data")
        result = await session.execute(
            text(PLAYER_ALIAS_QUERY), {"player_id": player_id}
        )
        result = result.fetchall()

    logger.info("Initial player data fetched")
    result = [{**row._asdict()} for row in result]
    for player in result:
        player["latest_updated_timestamp"] = player[
            "latest_updated_timestamp"
        ].isoformat()

    logger.info("Returning initial player data")
    return result


@router.websocket("/ws/player/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    connection_id = str(uuid.uuid4())
    await connection_manager.connect(websocket, player_id, connection_id)

    try:
        while True:
            data = await websocket.receive_text()
            # Do nothing with data for now
    except WebSocketDisconnect:
        connection_manager.disconnect(player_id, connection_id)
    finally:
        logger.info(
            "WebSocket connection for player %s with connection ID %s closed",
            player_id,
            connection_id,
        )
