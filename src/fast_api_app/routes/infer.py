import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from fast_api_app.connections import limiter, model_queue, redis_conn
from shared_lib.constants import (
    BUCKET_THRESHOLDS,
    MAIN_ONLY_ABILITIES,
    STANDARD_ABILITIES,
)

router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)


class InferenceRequest(BaseModel):
    abilities: dict[str, int]
    weapon_id: int


class InferenceResponse(BaseModel):
    predictions: list[tuple[str, float]]


# Create a persistent client
persistent_client = httpx.AsyncClient()


@router.get("/api/infer", response_class=HTMLResponse)
async def infer_instructions():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inference API Instructions</title>
</head>
<body>
    <h1>Inference API Instructions</h1>
    
    <p>This endpoint provides detailed instructions on how to use the inference API for Splatoon 3 gear ability predictions.</p>
    
    <h2>Endpoint Details</h2>
    <ul>
        <li><strong>Method:</strong> POST</li>
        <li><strong>Endpoint:</strong> /api/infer</li>
    </ul>

    <h2>Request Body</h2>
    <h3>abilities</h3>
    <p>A dictionary of ability names and their corresponding Ability Point (AP) values. Each ability is represented by an integer AP value, where:</p>
    <ul>
        <li>A main slot ability has a weight of 10 AP</li>
        <li>A sub slot ability has a weight of 3 AP</li>
        <li>Main-Slot-Only abilities should always be represented as 10 AP</li>
    </ul>
    <p>The total AP for an ability is the sum of its main and sub slot values. For example, one main (10 AP) and three subs (3 AP each) of Swim Speed Up would be represented as 19 AP.</p>

    <h3>weapon_id</h3>
    <p>An integer representing the unique identifier for a specific weapon in Splatoon 3.</p>

    <h2>Example Request</h2>
    <pre>
{
    "abilities": {
        "swim_speed_up": 19,
        "ninja_squid": 10,
        "intensify_action": 9,
        "stealth_jump": 10,
        "special_saver": 3,
        "quick_super_jump": 3,
        "ink_resist_up": 3
    },
    "weapon_id": 50
}
    </pre>

    <h2>Response</h2>
    <p>A list of tuples, each containing:</p>
    <ol>
        <li>An ability token (string)</li>
        <li>The predicted value for that token (float)</li>
    </ol>
    <p>Ability tokens are formatted as follows:</p>
    <ul>
        <li>For main-slot-only abilities: the ability name (e.g., 'ninja_squid')</li>
        <li>For standard abilities: the ability name followed by a number representing the AP breakpoint (e.g., 'swim_speed_up_3', 'swim_speed_up_6', etc.)</li>
    </ul>
    <p>The number in the token represents the minimum AP value for that prediction. For instance, 'swim_speed_up_3' represents the effect of Swim Speed Up with at least 3 AP.</p>

    <h2>Note</h2>
    <p>This endpoint is rate-limited to 10 requests per minute to ensure fair usage and system stability.</p>

    <h2>Ability Lists</h2>
    <h3>Main-Only Abilities</h3>
    <ul>
        """ + "".join([f"<li>{ability}</li>" for ability in MAIN_ONLY_ABILITIES]) + """
    </ul>

    <h3>Standard Abilities</h3>
    <ul>
        """ + "".join([f"<li>{ability}</li>" for ability in STANDARD_ABILITIES]) + """
    </ul>

    <h2>AP Breakpoints</h2>
    <ul>
        """ + "".join([f"<li>{breakpoint}</li>" for breakpoint in BUCKET_THRESHOLDS]) + """
    </ul>
</body>
</html>
    """)


@router.post("/api/infer")
@limiter.limit("10/minute")
async def infer(inference_request: InferenceRequest, request: Request):
    logger.info(f"Received inference request: {inference_request}")
    redis_key = "splatgpt"
    # Sort abilities by key, remove 0 and null values, and convert to string
    # for purposes of caching
    abilities_str = sorted(
        [
            f"{ability}:{value}"
            for ability, value in inference_request.abilities.items()
            if value > 0
        ]
    )
    abilities_str.append(f"weapon_id:{inference_request.weapon_id}")
    abilities_str = ",".join(abilities_str)
    abilities_hash = hash(abilities_str)
    cached_result = redis_conn.hget(redis_key, abilities_hash)
    if cached_result:
        logger.info(f"Cache hit for hash: {abilities_hash}")
        return InferenceResponse(predictions=eval(cached_result))

    logger.info(f"Cache miss for hash: {abilities_hash}")
    model_request = {
        "target": inference_request.abilities,
        "weapon_id": inference_request.weapon_id,
    }

    # Request to the model server using the persistent client
    logger.info(f"Sending request to model server: {model_request}")
    try:
        result = await model_queue.add_to_queue(model_request)
    except Exception as e:
        logger.error(f"Error sending request to model server: {e}")
        raise HTTPException(
            status_code=503, detail="Error sending request to model server"
        )

    logger.info(f"Received response from model server: {result}")
    redis_conn.hset(redis_key, abilities_hash, str(result["predictions"]))
    redis_conn.expire(redis_key, model_queue.cache_expiration)
    return InferenceResponse(predictions=result["predictions"])
