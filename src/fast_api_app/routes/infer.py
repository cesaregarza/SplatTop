import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

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


class ModelResponse(BaseModel):
    predictions: list[tuple[str, float]]
    splatgpt_info: dict
    api_version: str = "0.1.0"
    inference_time: float


class InferenceRequest(BaseModel):
    abilities: dict[str, int]
    weapon_id: int


class MetaData(BaseModel):
    request_id: str
    api_version: str
    splatgpt_version: str
    cache_status: str
    processing_time_ms: int


class InferenceResponse(BaseModel):
    predictions: list[tuple[str, float]]
    metadata: MetaData


# Create a persistent client
persistent_client = httpx.AsyncClient()


@router.get("/api/infer", response_class=HTMLResponse)
async def infer_instructions():
    return HTMLResponse(
        content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SplatGPT Inference API Instructions</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
        }
        
        h1, h2, h3 {
            color: #2c3e50;
            margin-top: 2rem;
        }
        
        h1 {
            border-bottom: 2px solid #eee;
            padding-bottom: 0.5rem;
        }
        
        pre {
            background-color: #f6f8fa;
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
        }
        
        code {
            background-color: #f6f8fa;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'Monaco', 'Consolas', monospace;
        }
        
        ul, ol {
            padding-left: 2rem;
        }
        
        li {
            margin: 0.5rem 0;
        }
        
        .endpoint {
            background-color: #e8f4f8;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }
        
        .note {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .special-token {
            font-family: monospace;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <h1>SplatGPT Inference API Instructions</h1>
    
    <p>This endpoint provides detailed instructions on how to use the inference API for Splatoon 3 gear ability predictions.</p>
    
    <div class="endpoint">
        <h2>Endpoint Details</h2>
        <ul>
            <li><strong>Method:</strong> POST</li>
            <li><strong>Endpoint:</strong> <code>/api/infer</code></li>
            <li><strong>Header:</strong> A custom User-Agent is required</li>
        </ul>
    </div>

    <h2>Request Headers</h2>
    <p>A custom User-Agent header is required for all requests to this endpoint. Requests without a custom User-Agent will be rejected.</p>

    <h2>Request Body</h2>
    
    <h3>abilities</h3>
    <p>A dictionary of ability names and their corresponding Ability Point (AP) values. Each ability is represented by an integer AP value, where:</p>
    <ul>
        <li>A main slot ability has a weight of <code>10 AP</code></li>
        <li>A sub slot ability has a weight of <code>3 AP</code></li>
        <li>Main-Slot-Only abilities should always be represented as <code>10 AP</code></li>
    </ul>
    <p>The total AP for an ability is the sum of its main and sub slot values. For example, one main (10 AP) and three subs (3 AP each) of Swim Speed Up would be represented as 19 AP.</p>

    <h3>weapon_id</h3>
    <p>An integer representing the unique identifier for a specific weapon in Splatoon 3. The internal ID, where 50 is the ID for 52 gal.</p>

    <h2>Example Request</h2>
    <pre>{
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
}</pre>

    <h2>Response</h2>
    <p>The response contains two main parts:</p>
    <ol>
        <li><strong>predictions:</strong> A list of tuples, each containing:
            <ul>
                <li>An ability token (string)</li>
                <li>The predicted value for that token (float)</li>
            </ul>
        </li>
        <li><strong>metadata:</strong> Additional information about the request and response, including:
            <ul>
                <li>request_id: A unique identifier for the request</li>
                <li>api_version: The version of the API used</li>
                <li>splatgpt_version: The version of the model used for prediction</li>
                <li>cache_status: Whether the result was retrieved from cache ("hit") or newly computed ("miss")</li>
                <li>processing_time_ms: The time taken to process the request, in milliseconds</li>
            </ul>
        </li>
    </ol>
    
    <p>Ability tokens are formatted as follows:</p>
    <ul>
        <li>For main-slot-only abilities: the ability name (e.g., <code>ninja_squid</code>)</li>
        <li>For standard abilities: the ability name followed by a number representing the AP breakpoint (e.g., <code>swim_speed_up_3</code>, <code>swim_speed_up_6</code>, etc.)</li>
    </ul>
    <p>The number in the token represents the minimum AP value for that prediction. For instance, <code>swim_speed_up_3</code> represents the effect of Swim Speed Up with at least 3 AP.</p>

    <div class="note">
        <h2>Note</h2>
        <p>This endpoint is rate-limited to 10 requests per minute to ensure fair usage and system stability.</p>
    </div>

    <h2>Ability Lists</h2>
    <h3>Main-Only Abilities</h3>
    <ul>
        """
        + "".join([f"<li>{ability}</li>" for ability in MAIN_ONLY_ABILITIES])
        + """
    </ul>

    <h3>Standard Abilities</h3>
    <ul>
        """
        + "".join([f"<li>{ability}</li>" for ability in STANDARD_ABILITIES])
        + """
    </ul>

    <h3>Special Tokens</h3>
    <p>There are special tokens that will be returned that should be close to zero probability in the output, here are the meanings:</p>
    <ul>
        <li><span class="special-token">&lt;NULL&gt;</span>: Placeholder token to build from no input, safe to ignore</li>
        <li><span class="special-token">&lt;PAD&gt;</span>: Padding token used in training, safe to ignore</li>
    </ul>

    <h2>AP Breakpoints</h2>
    <ul>
        """
        + "".join(
            [f"<li>{breakpoint}</li>" for breakpoint in BUCKET_THRESHOLDS]
        )
        + """
    </ul>
</body>
</html>
    """
    )


@asynccontextmanager
async def log_inference_request(
    request: Request,
    inference_request: InferenceRequest,
    model_response: ModelResponse | None = None,
):
    """Context manager to handle logging of inference requests"""
    request_id = uuid.uuid4()
    start_time = time.time()

    try:
        yield request_id
        status_code = 200
        error_message = None
    except Exception as e:
        status_code = getattr(e, "status_code", 500)
        error_message = str(e)
        raise
    finally:
        processing_time = int(
            (time.time() - start_time) * 1000
        )  # Convert to ms

        # Prepare log entry
        log_entry = {
            "request_id": request_id,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "http_method": request.method,
            "endpoint": str(request.url.path),
            "input_data": {
                "abilities": inference_request.abilities,
                "weapon_id": inference_request.weapon_id,
            },
            "splatgpt_version": model_response.splatgpt_info.get(
                "version", "unknown"
            )
            if model_response
            else "unknown",
            "processing_time_ms": processing_time,
            "status_code": status_code,
            "error_message": error_message,
        }

        # Add model-specific information if available
        if model_response:
            log_entry["output_data"] = {
                "predictions": model_response.predictions,
                "splatgpt_info": model_response.splatgpt_info,
                "api_version": model_response.api_version,
                "inference_time": model_response.inference_time,
            }

        # Log to database
        try:
            if os.environ.get("ENV") == "development":
                logger.info(
                    "Not logging inference request in development environment"
                )
                logger.info(log_entry)
            else:
                async with request.app.state.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO splatgpt.model_inference_logs (
                            request_id, ip_address, user_agent, http_method,
                            endpoint, input_data, model_version,
                            processing_time_ms, status_code, error_message,
                            output_data
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
                        )
                    """,
                        request_id,
                        log_entry["ip_address"],
                        log_entry["user_agent"],
                        log_entry["http_method"],
                        log_entry["endpoint"],
                        log_entry["input_data"],
                        log_entry["model_version"],
                        log_entry["processing_time_ms"],
                        log_entry["status_code"],
                        log_entry["error_message"],
                        log_entry.get("output_data"),
                    )
        except Exception as db_error:
            logger.error(f"Failed to log inference request: {db_error}")


@router.post("/api/infer")
@limiter.limit("10/minute")
async def infer(inference_request: InferenceRequest, request: Request):
    # Check for custom User-Agent
    user_agent = request.headers.get("User-Agent")
    if not user_agent or user_agent in ["Mozilla/5.0", "PostmanRuntime/7.32.2"]:
        raise HTTPException(
            status_code=400, detail="Custom User-Agent header is required"
        )

    # Check request size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1024:
        raise HTTPException(status_code=413, detail="Request too large")

    cache_status = "miss"
    model_response = None

    async with log_inference_request(request, inference_request) as request_id:
        logger.info(
            f"Received inference request {request_id}: {inference_request}"
        )

        redis_key = "splatgpt"
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

        processing_start = time.time()

        if cached_result:
            logger.info(
                f"Cache hit for request {request_id}, hash: {abilities_hash}"
            )
            cache_status = "hit"
            predictions = eval(cached_result)
        else:
            logger.info(
                f"Cache miss for request {request_id}, hash: {abilities_hash}"
            )
            model_request = {
                "target": inference_request.abilities,
                "weapon_id": inference_request.weapon_id,
            }

            logger.info(
                f"Sending request {request_id} to model server: {model_request}"
            )
            try:
                raw_result = await model_queue.add_to_queue(model_request)
                model_response = ModelResponse(**raw_result)
                predictions = model_response.predictions

                redis_conn.hset(redis_key, abilities_hash, str(predictions))
                redis_conn.expire(redis_key, model_queue.cache_expiration)

            except Exception as e:
                logger.error(
                    f"Error sending request {request_id} to model server: {e}"
                )
                raise HTTPException(
                    status_code=503,
                    detail="Error sending request to model server",
                )

        processing_time = int((time.time() - processing_start) * 1000)

        return InferenceResponse(
            predictions=predictions,
            metadata={
                "request_id": str(request_id),
                "api_version": model_response.api_version
                if model_response
                else "0.1.0",
                "splatgpt_version": model_response.splatgpt_info.get(
                    "version", "unknown"
                )
                if model_response
                else "unknown",
                "cache_status": cache_status,
                "processing_time_ms": processing_time,
            },
        )
