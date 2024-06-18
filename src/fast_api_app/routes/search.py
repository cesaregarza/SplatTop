import logging

from fastapi import APIRouter, HTTPException, Request

from fast_api_app.connections import limiter, redis_conn, sqlite_cursor
from shared_lib.constants import AUTOMATON_IS_VALID_REDIS_KEY

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/search/{query}")
@limiter.limit("10/second")
async def search(query: str, request: Request):
    if not redis_conn.get(AUTOMATON_IS_VALID_REDIS_KEY):
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )

    logger.info(f"Searching for: {query}")
    formatted_key = f"%{query}%"
    sqlite_cursor.execute(
        "SELECT key, value FROM player_data WHERE key LIKE ? LIMIT 10",
        (formatted_key,),
    )
    logger.info(f"Search complete for: {query}")
    return sqlite_cursor.fetchall()
