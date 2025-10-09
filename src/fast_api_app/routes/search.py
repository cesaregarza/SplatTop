import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException, Request

from fast_api_app.connections import limiter, redis_conn, sqlite_cursor
from shared_lib.constants import AUTOMATON_IS_VALID_REDIS_KEY
from shared_lib.monitoring import (
    SEARCH_LATENCY,
    SEARCH_RESULTS,
    metrics_enabled,
)

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
    start = perf_counter()
    sqlite_cursor.execute(
        "SELECT alias, player_id FROM aliases WHERE alias LIKE ? LIMIT 10",
        (formatted_key,),
    )
    result = sqlite_cursor.fetchall()
    duration = perf_counter() - start
    outcome = "hit" if result else "miss"
    if metrics_enabled():
        SEARCH_LATENCY.labels(outcome=outcome).observe(duration)
        SEARCH_RESULTS.labels(outcome=outcome).inc()
    logger.info(f"Search complete for: {query}")
    return result
