import logging

import orjson
from fastapi import APIRouter, HTTPException

from flask_app.connections import redis_conn
from shared_lib.constants import ALIASES_REDIS_KEY

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/api/search/{query}")
async def search(query: str):
    aliases_data = redis_conn.get(ALIASES_REDIS_KEY)
    if not aliases_data:
        raise HTTPException(
            status_code=503,
            detail="Data is not available yet, please wait.",
        )

    aliases = orjson.loads(aliases_data)
    return [
        (alias, player_id)
        for alias, player_id in aliases.items()
        if query in alias
    ]
