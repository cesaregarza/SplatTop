import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException, Request

from fast_api_app.connections import limiter, redis_conn
from fast_api_app.sqlite_lookup_store import lookup_fetchall
from shared_lib.constants import LOOKUP_SQLITE_SNAPSHOT_META_KEY
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
    if not redis_conn.get(LOOKUP_SQLITE_SNAPSHOT_META_KEY):
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )

    logger.info(f"Searching for: {query}")
    formatted_key = f"%{query}%"
    start = perf_counter()
    result = lookup_fetchall(
        "SELECT alias, player_id FROM aliases WHERE alias LIKE ? LIMIT 10",
        (formatted_key,),
    )
    duration = perf_counter() - start
    outcome = "hit" if result else "miss"
    if metrics_enabled():
        SEARCH_LATENCY.labels(outcome=outcome).observe(duration)
        SEARCH_RESULTS.labels(outcome=outcome).inc()
    logger.info(f"Search complete for: {query}")
    return result
