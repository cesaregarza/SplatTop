from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from celery_app.connections import Session, redis_conn
from shared_lib.constants import API_USAGE_QUEUE_KEY


def _ensure_schema() -> None:
    # Create schema and tables if they do not exist
    with Session() as session:
        session.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS auth.api_tokens (
                    id UUID PRIMARY KEY,
                    name TEXT NOT NULL,
                    hash TEXT NOT NULL UNIQUE,
                    scopes TEXT[],
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMPTZ NULL,
                    revoked_at TIMESTAMPTZ NULL,
                    last_used_at TIMESTAMPTZ NULL,
                    usage_count BIGINT NOT NULL DEFAULT 0
                );
                """
            )
        )
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS auth.api_token_usage (
                    id BIGSERIAL PRIMARY KEY,
                    token_id UUID NOT NULL REFERENCES auth.api_tokens(id),
                    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    ip INET NULL,
                    path TEXT NOT NULL,
                    user_agent TEXT NULL,
                    status SMALLINT NULL,
                    latency_ms INTEGER NULL
                );
                """
            )
        )
        session.commit()


def persist_api_token(
    token_id: str,
    name: str,
    token_hash: str,
    scopes: List[str],
    expires_at_ms: Optional[int],
) -> None:
    _ensure_schema()
    with Session() as session:
        # Upsert-like behavior
        session.execute(
            text(
                """
                INSERT INTO auth.api_tokens (id, name, hash, scopes, expires_at)
                VALUES (:id, :name, :hash, :scopes, to_timestamp(:expires))
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    hash = EXCLUDED.hash,
                    scopes = EXCLUDED.scopes,
                    expires_at = EXCLUDED.expires_at
                """
            ),
            {
                "id": token_id,
                "name": name,
                "hash": token_hash,
                "scopes": scopes,
                # Convert ms to seconds once; to_timestamp(NULL) yields NULL
                "expires": (expires_at_ms / 1000.0) if expires_at_ms else None,
            },
        )
        session.commit()


def revoke_api_token(token_id: str) -> None:
    _ensure_schema()
    with Session() as session:
        session.execute(
            text(
                "UPDATE auth.api_tokens SET revoked_at = NOW() WHERE id = :id"
            ),
            {"id": token_id},
        )
        session.commit()


def flush_api_usage(batch_size: int | None = None) -> int:
    """Flush usage events atomically using a processing list.

    Moves items with RPOPLPUSH from the main queue to a processing list,
    writes them to DB, then removes them from processing. On failure,
    moves items back to the main queue to avoid data loss.
    """
    import os

    _ensure_schema()
    bs = batch_size or int(os.getenv("API_USAGE_FLUSH_BATCH", "1000"))
    processing_key = f"{API_USAGE_QUEUE_KEY}:processing"

    events: List[Dict[str, Any]] = []
    raw_items: List[str] = []

    # Atomically move up to bs items to processing
    for _ in range(bs):
        item = redis_conn.rpoplpush(API_USAGE_QUEUE_KEY, processing_key)
        if item is None:
            break
        raw_items.append(item)
        try:
            events.append(json.loads(item))
        except Exception:
            # Drop malformed, remove from processing
            redis_conn.lrem(processing_key, 1, item)
            continue

    if not events:
        return 0

    try:
        with Session() as session:
            for e in events:
                session.execute(
                    text(
                        """
                        INSERT INTO auth.api_token_usage (token_id, ts, ip, path, user_agent, status, latency_ms)
                        VALUES (:token_id, to_timestamp(:ts), :ip, :path, :ua, :status, :latency_ms)
                        """
                    ),
                    {
                        "token_id": e.get("token_id"),
                        "ts": (
                            e.get("ts_ms", int(time.time() * 1000)) / 1000.0
                        ),
                        "ip": e.get("ip"),
                        "path": e.get("path"),
                        "ua": e.get("ua"),
                        "status": e.get("status"),
                        "latency_ms": e.get("latency_ms"),
                    },
                )
                if e.get("token_id"):
                    session.execute(
                        text(
                            "UPDATE auth.api_tokens SET last_used_at = NOW(), usage_count = usage_count + 1 WHERE id = :id"
                        ),
                        {"id": e.get("token_id")},
                    )
            session.commit()
    except Exception:
        # Requeue items back on failure
        for raw in raw_items:
            redis_conn.lrem(processing_key, 1, raw)
            redis_conn.rpush(API_USAGE_QUEUE_KEY, raw)
        raise
    else:
        # Remove processed items
        for raw in raw_items:
            redis_conn.lrem(processing_key, 1, raw)
        return len(events)
