import logging

from fastapi import APIRouter, HTTPException, Request

from fast_api_app.connections import limiter, redis_conn
from fast_api_app.memory_sqlite import search_data
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
    return search_data(query)[:10]
