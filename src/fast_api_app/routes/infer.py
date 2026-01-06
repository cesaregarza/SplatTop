import logging
import os
import time
import traceback
import uuid
from contextlib import asynccontextmanager

import httpx
import orjson
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from fast_api_app.connections import (
    async_session,
    limiter,
    model_queue,
    redis_conn,
)
from fast_api_app.utils import get_client_ip
from shared_lib.constants import (
    BUCKET_THRESHOLDS,
    MAIN_ONLY_ABILITIES,
    STANDARD_ABILITIES,
)
from shared_lib.models import FeedbackLog, ModelInferenceLog
from shared_lib.monitoring import (
    SPLATGPT_CACHE_REQUESTS,
    SPLATGPT_ERRORS,
    SPLATGPT_INFERENCE_DURATION,
    metrics_enabled,
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


class FeedbackRequest(BaseModel):
    request_id: str
    user_agent: str
    feedback: bool


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
    <title>SplatGPT API Documentation</title>
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

        .section {
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            margin: 2rem 0;
            padding: 1rem;
        }

        .implementation-details {
            background-color: #f8f9fa;
            margin-top: 3rem;
            padding: 1.5rem;
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <h1>SplatGPT API Documentation</h1>
    
    <div class="section">
        <h2>Core API Endpoints</h2>

        <h3>1. Inference Endpoint</h3>
        <div class="endpoint">
            <h4>Endpoint Details</h4>
            <ul>
                <li><strong>Method:</strong> POST</li>
                <li><strong>Endpoint:</strong> <code>/api/infer</code></li>
                <li><strong>Header:</strong> A custom User-Agent is required</li>
            </ul>
        </div>

        <h4>Request Headers</h4>
        <p>A custom User-Agent header is required for all requests to this endpoint. Requests without a custom User-Agent will be rejected.</p>

        <h4>Request Body</h4>
        <h5>abilities</h5>
        <p>A dictionary of ability names and their corresponding Ability Point (AP) values. Each ability is represented by an integer AP value, where:</p>
        <ul>
            <li>A main slot ability has a weight of <code>10 AP</code></li>
            <li>A sub slot ability has a weight of <code>3 AP</code></li>
            <li>Main-Slot-Only abilities should always be represented as <code>10 AP</code></li>
        </ul>

        <h5>weapon_id</h5>
        <p>An integer representing the unique identifier for a specific weapon in Splatoon 3. The internal ID, where 50 is the ID for 52 gal.</p>

        <h4>Example Inference Request</h4>
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

        <h4>Inference Response</h4>
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

        <div class="note">
            <p>The inference endpoint is rate-limited to 10 requests per minute to ensure fair usage and system stability.</p>
        </div>

        <h3>2. Feedback Endpoint</h3>
        <div class="endpoint">
            <h4>Endpoint Details</h4>
            <ul>
                <li><strong>Method:</strong> POST</li>
                <li><strong>Endpoint:</strong> <code>/api/feedback</code></li>
            </ul>
        </div>

        <p>The feedback endpoint allows users to provide feedback on inference predictions.</p>

        <h4>Feedback Request Body</h4>
        <pre>{
    "request_id": "string",  // The request_id from the inference response
    "user_agent": "string",  // The User-Agent used in the request
    "feedback": boolean      // true for positive feedback, false for negative
}</pre>

        <h4>Feedback Response</h4>
        <p>Upon successful submission, the endpoint returns a status message indicating whether the feedback was inserted or updated:</p>
        <pre>{
    "status": "Feedback updated successfully" // or "New feedback inserted successfully"
}</pre>
    </div>

    <div class="implementation-details">
        <h2>Implementation Details</h2>

        <h3>Token Format</h3>
        <p>Ability tokens in the response follow these formatting rules:</p>
        <ul>
            <li>For main-slot-only abilities: the ability name (e.g., <code>ninja_squid</code>)</li>
            <li>For standard abilities: the ability name followed by a number representing the AP breakpoint (e.g., <code>swim_speed_up_3</code>, <code>swim_speed_up_6</code>, etc.)</li>
        </ul>
        <p>The number in the token represents the minimum AP value for that prediction. For instance, <code>swim_speed_up_3</code> represents the effect of Swim Speed Up with at least 3 AP.</p>

        <h3>Special Tokens</h3>
        <p>These special tokens may appear in the output with near-zero probability:</p>
        <ul>
            <li><span class="special-token">&lt;NULL&gt;</span>: Placeholder token to build from no input, safe to ignore</li>
            <li><span class="special-token">&lt;PAD&gt;</span>: Padding token used in training, safe to ignore</li>
        </ul>

        <h3>Available Abilities</h3>
        <h4>Main-Only Abilities</h4>
        <ul>
            """
        + "".join([f"<li>{ability}</li>" for ability in MAIN_ONLY_ABILITIES])
        + """
        </ul>

        <h4>Standard Abilities</h4>
        <ul>
            """
        + "".join([f"<li>{ability}</li>" for ability in STANDARD_ABILITIES])
        + """
        </ul>

        <h3>AP Breakpoints</h3>
        <ul>
            """
        + "".join(
            [f"<li>{breakpoint}</li>" for breakpoint in BUCKET_THRESHOLDS]
        )
        + """
        </ul>
    </div>
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
            "ip_address": get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "http_method": request.method,
            "endpoint": str(request.url.path),
            "input_data": {
                "abilities": inference_request.abilities,
                "weapon_id": inference_request.weapon_id,
            },
            "model_version": model_response.splatgpt_info.get(
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
        logger.info(log_entry)
        try:
            if os.environ.get("ENV") == "development":
                logger.info(
                    "Not logging inference request in development environment"
                )
            else:
                async with async_session() as session:
                    new_log_entry = ModelInferenceLog(
                        request_id=request_id,
                        ip_address=log_entry["ip_address"],
                        user_agent=log_entry["user_agent"],
                        http_method=log_entry["http_method"],
                        endpoint=log_entry["endpoint"],
                        input_data=log_entry["input_data"],
                        model_version=log_entry["model_version"],
                        processing_time_ms=log_entry["processing_time_ms"],
                        status_code=log_entry["status_code"],
                        error_message=log_entry["error_message"],
                        output_data=log_entry.get("output_data"),
                    )
                    session.add(new_log_entry)
                    await session.commit()
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
    predictions: list | None = None

    processing_start = time.time()

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

    model_request: dict | None = None

    if cached_result:
        logger.info(f"Cache hit, hash: {abilities_hash}")
        cache_status = "hit"
        try:
            predictions = orjson.loads(cached_result)
        except Exception:
            if metrics_enabled():
                SPLATGPT_ERRORS.labels(stage="cache_deserialize").inc()
            logger.exception("Failed to deserialize cached inference payload")
            cache_status = "miss"
            predictions = None
            model_request = {
                "target": inference_request.abilities,
                "weapon_id": inference_request.weapon_id,
            }
    else:
        logger.info(f"Cache miss, hash: {abilities_hash}")
        model_request = {
            "target": inference_request.abilities,
            "weapon_id": inference_request.weapon_id,
        }

    if metrics_enabled():
        SPLATGPT_CACHE_REQUESTS.labels(status=cache_status).inc()

    if predictions is None:
        if model_request is None:
            model_request = {
                "target": inference_request.abilities,
                "weapon_id": inference_request.weapon_id,
            }
        try:
            raw_result = await model_queue.add_to_queue(model_request)
            model_response = ModelResponse(**raw_result)
            predictions = model_response.predictions

            try:
                pipe = redis_conn.pipeline(transaction=True)
                pipe.hset(redis_key, abilities_hash, orjson.dumps(predictions))
                pipe.expire(redis_key, model_queue.cache_expiration)
                pipe.execute()
            except RedisError:
                logger.warning(
                    "Failed to persist model predictions to redis cache",
                    exc_info=True,
                )

        except Exception as e:
            logger.error(f"Error sending request to model server: {e}")
            if metrics_enabled():
                SPLATGPT_ERRORS.labels(stage="model_request").inc()
            raise HTTPException(
                status_code=503,
                detail="Error sending request to model server",
            )

    processing_time = int((time.time() - processing_start) * 1000)
    if metrics_enabled() and cache_status in {"hit", "miss"}:
        source = "cache" if cache_status == "hit" else "model"
        SPLATGPT_INFERENCE_DURATION.labels(source=source).observe(
            processing_time / 1000.0
        )

    # Now wrap the response generation with the context manager, passing model_response
    async with log_inference_request(
        request, inference_request, model_response
    ) as request_id:
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


@router.post("/api/feedback")
async def feedback(feedback_request: FeedbackRequest):
    try:
        async with async_session() as session:
            stmt = (
                pg_insert(FeedbackLog)
                .values(
                    request_id=feedback_request.request_id,
                    user_agent=feedback_request.user_agent,
                    feedback=feedback_request.feedback,
                )
                .on_conflict_do_update(
                    index_elements=["request_id"],
                    set_={"feedback": feedback_request.feedback},
                )
            )
            result = await session.execute(stmt)
            await session.commit()

        status_message = (
            "Feedback updated"
            if result.rowcount > 0
            else "New feedback inserted"
        )
        return {"status": f"{status_message} successfully"}

    except Exception as e:
        logger.error(f"Error logging feedback: {e}")
        raise HTTPException(status_code=500, detail="Error logging feedback")
