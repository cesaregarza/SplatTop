import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional

import orjson
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from fast_api_app.auth import hash_secret as _hash_secret
from fast_api_app.auth import require_admin_token as _require_admin_token
from fast_api_app.connections import celery, limiter, redis_conn
from shared_lib.constants import (
    API_TOKEN_HASH_MAP_PREFIX,
    API_TOKEN_IDS_SET,
    API_TOKEN_META_PREFIX,
    API_TOKEN_PREFIX,
    API_TOKENS_ACTIVE_SET,
)


def require_admin_token(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_admin_token: Optional[str] = Header(
        default=None, convert_underscores=False
    ),
):
    """Thin wrapper to stabilize dependency identity for overrides in tests.

    Delegates to fast_api_app.auth.require_admin_token while providing a stable
    function object within this module that FastAPI can reference in
    router-level dependencies, ensuring client.app.dependency_overrides targeting
    fast_api_app.routes.admin_tokens.require_admin_token reliably takes effect
    even if fast_api_app.auth is reloaded in other tests.
    """
    return _require_admin_token(
        request,
        authorization=authorization,
        x_admin_token=x_admin_token,
    )


router = APIRouter(
    prefix="/api/admin/tokens", dependencies=[Depends(require_admin_token)]
)


class MintTokenRequest(BaseModel):
    name: str = Field(
        ...,
        description="Human-friendly token name",
        min_length=1,
        max_length=64,
    )
    note: Optional[str] = Field(
        default=None,
        description="Free-form note for who/what it's for",
        max_length=512,
    )
    scopes: Optional[List[str]] = Field(default=None)
    expires_at_ms: Optional[int] = Field(default=None)


class MintTokenResponse(BaseModel):
    id: str
    name: str
    note: Optional[str] = None
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
@limiter.limit("50/minute")
def mint_token(req: MintTokenRequest, request: Request):
    # Enforce a global cap to prevent unbounded token creation
    try:
        max_tokens = int(os.getenv("ADMIN_MAX_API_TOKENS", "1000"))
    except Exception:
        max_tokens = 1000
    current = _safe_scard(API_TOKENS_ACTIVE_SET)
    if max_tokens and current >= max_tokens:
        raise HTTPException(
            status_code=429, detail="API token limit reached; cannot mint more"
        )
    token_id = str(uuid.uuid4())
    # token_id is a non-secret identifier; uuid4 uses os.urandom under CPython
    # and is sufficient as an opaque ID (nitpick doc: security does not depend on it).
    # 32 random bytes (~256 bits entropy) -> ~43 char URL-safe string
    import secrets

    secret = secrets.token_urlsafe(32)
    token = f"{API_TOKEN_PREFIX}_{token_id}_{secret}"
    h = _hash_secret(secret)

    now_ms = int(time.time() * 1000)
    # Validate requested scopes if an allowlist is configured; otherwise apply a
    # conservative regex for hygiene.
    allowed_env = os.getenv("API_TOKEN_ALLOWED_SCOPES", "")
    allowed = {s.strip() for s in allowed_env.split(",") if s.strip()}
    scope_re = re.compile(r"^[A-Za-z0-9:._-]{1,64}$")
    # Default scopes ensure basic access unless narrowed explicitly.
    default_scopes = ["ripple.read", "misc.ping"]
    scopes_in = (
        list(req.scopes) if req.scopes is not None else list(default_scopes)
    )
    if allowed:
        unknown = [s for s in scopes_in if s not in allowed]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown scopes: {', '.join(sorted(set(unknown)))}",
            )
    else:
        bad = [s for s in scopes_in if not scope_re.match(s or "")]
        if bad:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scope format: {', '.join(sorted(set(bad)))}",
            )

    # Expiration must be in the future if provided
    if req.expires_at_ms and req.expires_at_ms < now_ms:
        raise HTTPException(
            status_code=400, detail="expires_at_ms must be in the future"
        )

    scopes_json = orjson.dumps(scopes_in).decode()

    try:
        pipe = redis_conn.pipeline()
        pipe.sadd(API_TOKENS_ACTIVE_SET, h)
        pipe.set(f"{API_TOKEN_HASH_MAP_PREFIX}{h}", token_id)
        pipe.hset(
            f"{API_TOKEN_META_PREFIX}{token_id}",
            mapping={
                "id": token_id,
                "name": req.name,
                "note": (req.note or ""),
                "hash": h,
                "scopes": scopes_json,
                "created_at_ms": now_ms,
                "expires_at_ms": req.expires_at_ms or 0,
                "revoked": 0,
            },
        )
        pipe.sadd(API_TOKEN_IDS_SET, token_id)
        pipe.execute()
    except Exception:
        raise HTTPException(status_code=503, detail="Token store unavailable")

    # Persist asynchronously
    celery.send_task(
        "tasks.persist_api_token",
        args=[
            token_id,
            req.name,
            (req.note or None),
            h,
            scopes_in,
            req.expires_at_ms,
        ],
    )

    return MintTokenResponse(
        id=token_id,
        name=req.name,
        note=req.note,
        token=token,
        scopes=scopes_in,
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
                    "note": meta.get("note") or None,
                    "scopes": scopes,
                    "created_at_ms": int(meta.get("created_at_ms", 0) or 0),
                    "expires_at_ms": int(meta.get("expires_at_ms", 0) or 0),
                    "revoked": int(meta.get("revoked", 0) or 0),
                }
            )
    # sort newest first
    tokens.sort(key=lambda x: x.get("created_at_ms", 0), reverse=True)
    return {"tokens": tokens}
