import hmac
import logging
import os
import time
from functools import lru_cache
from typing import Dict, Optional

import orjson
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from fast_api_app.auth import require_api_token as _require_api_token
from fast_api_app.connections import limiter
from fast_api_app.deployments import (
    DeploymentConfigError,
    DeploymentTarget,
    KubernetesRolloutError,
    deployment_targets,
    reload_deployment_targets,
    reset_kubernetes_client,
    trigger_rolling_update,
)

logger = logging.getLogger(__name__)


def require_api_token(request, authorization=None, x_api_token=None):
    """Stable wrapper around :func:`require_api_token` for dependency overrides."""
    return _require_api_token(
        request, authorization=authorization, x_api_token=x_api_token
    )


router = APIRouter(
    prefix="/api/webhooks/deployments",
    tags=["webhooks"],
    dependencies=[Depends(require_api_token)],
)


class WebhookInstruction(BaseModel):
    target: str = Field(..., description="Deployment target slug")
    image: Optional[str] = Field(
        default=None,
        description="Full container image reference to deploy",
        max_length=512,
    )
    sha: Optional[str] = Field(
        default=None,
        description="Git commit SHA to annotate rollout with",
        max_length=128,
    )
    annotations: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional annotations to apply to the pod template",
    )


class WebhookResponse(BaseModel):
    status: str
    target: str
    namespace: str
    deployment: str
    image: Optional[str]
    commit_sha: Optional[str] = Field(default=None, alias="commitSha")
    annotations: Dict[str, str]

    class Config:
        populate_by_name = True


def _require_secret() -> bytes:
    secret = os.getenv("DEPLOY_WEBHOOK_SECRET")
    if not secret:
        logger.error("DEPLOY_WEBHOOK_SECRET is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret is not configured",
        )
    return secret.encode()


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = os.getenv("DEPLOY_WEBHOOK_FERNET_KEY")
    if not key:
        logger.error("DEPLOY_WEBHOOK_FERNET_KEY is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook encryption key is not configured",
        )
    try:
        return Fernet(key.encode())
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Invalid Fernet key configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Invalid webhook encryption key",
        )


def reset_webhook_state() -> None:
    """Utility for tests to reset cached state."""
    _fernet.cache_clear()
    reload_deployment_targets()
    reset_kubernetes_client()


def _validate_timestamp(header_value: Optional[str]) -> str:
    if not header_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Timestamp header",
        )
    try:
        ts = int(header_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Timestamp header",
        )
    max_skew = int(os.getenv("DEPLOY_WEBHOOK_MAX_SKEW_SECONDS", "300"))
    now = int(time.time())
    if abs(now - ts) > max_skew:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Timestamp outside allowable window",
        )
    return str(ts)


def _validate_signature(
    provided: Optional[str], secret: bytes, timestamp: str, body: bytes
) -> None:
    if not provided or not provided.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-Signature-256 header",
        )
    provided_sig = provided.split("=", 1)[1]
    try:
        body_text = body.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be UTF-8 encoded",
        )
    message = f"{timestamp}\n{body_text}".encode()
    expected = hmac.new(secret, msg=message, digestmod="sha256").hexdigest()
    if not hmac.compare_digest(provided_sig, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )


def _parse_instruction(raw_body: bytes) -> WebhookInstruction:
    try:
        envelope = orjson.loads(raw_body)
    except orjson.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be valid JSON",
        )
    if not isinstance(envelope, dict) or "token" not in envelope:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Encrypted payload missing 'token'",
        )
    token = envelope.get("token")
    if not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'token' must be a string",
        )
    f = _fernet()
    ttl = int(os.getenv("DEPLOY_WEBHOOK_TOKEN_TTL_SECONDS", "600"))
    try:
        decrypted = f.decrypt(token.encode(), ttl=ttl)
    except InvalidToken:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to decrypt payload",
        )
    try:
        payload = orjson.loads(decrypted)
    except orjson.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decrypted payload must be valid JSON",
        )
    try:
        return WebhookInstruction.model_validate(payload)
    except Exception as exc:
        logger.warning("Invalid webhook payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deployment payload",
        )


def _resolve_target(slug: str) -> DeploymentTarget:
    try:
        targets = deployment_targets()
    except DeploymentConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    target = targets.get(slug)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown deployment target '{slug}'",
        )
    return target


@router.post("/rollout", response_model=WebhookResponse)
@limiter.limit("20/minute")
async def rollout(request: Request) -> WebhookResponse:
    raw_body = await request.body()
    timestamp = _validate_timestamp(request.headers.get("X-Timestamp"))
    secret = _require_secret()
    _validate_signature(
        request.headers.get("X-Signature-256"), secret, timestamp, raw_body
    )

    instruction = _parse_instruction(raw_body)
    target = _resolve_target(instruction.target)

    extra_annotations = instruction.annotations or {}

    try:
        annotations = trigger_rolling_update(
            target=target,
            image=instruction.image,
            commit_sha=instruction.sha,
            extra_annotations=extra_annotations,
        )
    except DeploymentConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except KubernetesRolloutError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    logger.info(
        "Triggered rollout for %s/%s using image '%s'",
        target.namespace,
        target.deployment,
        instruction.image,
    )

    return WebhookResponse(
        status="accepted",
        target=instruction.target,
        namespace=target.namespace,
        deployment=target.deployment,
        image=instruction.image,
        commit_sha=instruction.sha,
        annotations=annotations,
    )
