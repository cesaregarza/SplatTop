import time
import uuid
from typing import Any, Dict, List, Optional

import orjson
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from fast_api_app.auth import hash_secret, require_admin_token
from fast_api_app.connections import celery, limiter, redis_conn
from shared_lib.constants import (
    API_TOKEN_HASH_MAP_PREFIX,
    API_TOKEN_IDS_SET,
    API_TOKEN_META_PREFIX,
    API_TOKEN_PREFIX,
    API_TOKENS_ACTIVE_SET,
)

router = APIRouter(
    prefix="/api/admin/tokens", dependencies=[Depends(require_admin_token)]
)


class MintTokenRequest(BaseModel):
    name: str = Field(..., description="Human-friendly token name")
    scopes: Optional[List[str]] = Field(default=None)
    expires_at_ms: Optional[int] = Field(default=None)


class MintTokenResponse(BaseModel):
    id: str
    name: str
    token: str
    scopes: Optional[List[str]] = None
    expires_at_ms: Optional[int] = None
    created_at_ms: int


def _safe_scard(key: str) -> int:
    try:
        return int(redis_conn.scard(key))
    except Exception:
        try:
            return len(redis_conn.smembers(key))
        except Exception:
            return 0


@router.post("", response_model=MintTokenResponse)
@limiter.limit("5/minute")
def mint_token(req: MintTokenRequest, request: Request):
    # Enforce a global cap to prevent unbounded token creation
    import os

    try:
        max_tokens = int(os.getenv("ADMIN_MAX_API_TOKENS", "1000"))
    except Exception:
        max_tokens = 1000
    current = _safe_scard(API_TOKEN_IDS_SET)
    if max_tokens and current >= max_tokens:
        raise HTTPException(
            status_code=429, detail="API token limit reached; cannot mint more"
        )
    token_id = str(uuid.uuid4())
    # 32 bytes -> ~43 char url-safe
    import secrets

    secret = secrets.token_urlsafe(32)
    token = f"{API_TOKEN_PREFIX}_{token_id}_{secret}"
    h = hash_secret(secret)

    now_ms = int(time.time() * 1000)
    scopes_json = orjson.dumps(req.scopes or []).decode()

    pipe = redis_conn.pipeline()
    pipe.sadd(API_TOKENS_ACTIVE_SET, h)
    pipe.set(f"{API_TOKEN_HASH_MAP_PREFIX}{h}", token_id)
    pipe.hset(
        f"{API_TOKEN_META_PREFIX}{token_id}",
        mapping={
            "id": token_id,
            "name": req.name,
            "hash": h,
            "scopes": scopes_json,
            "created_at_ms": now_ms,
            "expires_at_ms": req.expires_at_ms or 0,
            "revoked": 0,
        },
    )
    pipe.sadd(API_TOKEN_IDS_SET, token_id)
    pipe.execute()

    # Persist asynchronously
    celery.send_task(
        "tasks.persist_api_token",
        args=[token_id, req.name, h, req.scopes or [], req.expires_at_ms],
    )

    return MintTokenResponse(
        id=token_id,
        name=req.name,
        token=token,
        scopes=req.scopes or [],
        expires_at_ms=req.expires_at_ms,
        created_at_ms=now_ms,
    )


@router.delete("/{token_id}")
def revoke_token(token_id: str):
    meta_key = f"{API_TOKEN_META_PREFIX}{token_id}"
    meta = redis_conn.hgetall(meta_key)
    if not meta:
        raise HTTPException(status_code=404, detail="Token not found")
    h = meta.get("hash")
    pipe = redis_conn.pipeline()
    if h:
        pipe.srem(API_TOKENS_ACTIVE_SET, h)
        pipe.delete(f"{API_TOKEN_HASH_MAP_PREFIX}{h}")
    pipe.hset(
        meta_key,
        mapping={"revoked": 1, "revoked_at_ms": int(time.time() * 1000)},
    )
    pipe.execute()

    celery.send_task("tasks.revoke_api_token", args=[token_id])
    return {"status": "revoked", "id": token_id}


@router.get("")
def list_tokens():
    ids = list(redis_conn.smembers(API_TOKEN_IDS_SET))
    tokens: List[Dict[str, Any]] = []
    if not ids:
        return {"tokens": tokens}

    pipe = redis_conn.pipeline()
    for tid in ids:
        pipe.hgetall(f"{API_TOKEN_META_PREFIX}{tid}")
    results = pipe.execute()

    for meta in results:
        if meta:
            scopes = []
            try:
                scopes = orjson.loads(meta.get("scopes", "[]"))
            except Exception:
                pass
            tokens.append(
                {
                    "id": meta.get("id"),
                    "name": meta.get("name"),
                    "scopes": scopes,
                    "created_at_ms": int(meta.get("created_at_ms", 0) or 0),
                    "expires_at_ms": int(meta.get("expires_at_ms", 0) or 0),
                    "revoked": int(meta.get("revoked", 0) or 0),
                }
            )
    # sort newest first
    tokens.sort(key=lambda x: x.get("created_at_ms", 0), reverse=True)
    return {"tokens": tokens}
