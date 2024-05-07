import logging

import orjson
from fastapi import APIRouter, HTTPException

from flask_app.connections import redis_conn
from flask_app.memory_sqlite import search_data
from shared_lib.constants import AUTOMATON_IS_VALID_REDIS_KEY

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/search/{query}")
async def search(query: str):
    if not redis_conn.get(AUTOMATON_IS_VALID_REDIS_KEY):
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )

    logger.info(f"Searching for: {query}")
    return search_data(query)


