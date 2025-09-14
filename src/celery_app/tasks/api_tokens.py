from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from celery_app.connections import Session, redis_conn
from shared_lib.constants import API_TOKEN_META_PREFIX, API_USAGE_QUEUE_KEY


def _ensure_schema() -> None:
    # No-op: assume schema/tables are managed externally (migrations/admin)
    return


def persist_api_token(
    token_id: str,
    name: str,
    note: Optional[str],
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
                INSERT INTO auth.api_tokens (id, name, note, hash, scopes, expires_at)
                VALUES (:id, :name, :note, :hash, :scopes, to_timestamp(:expires))
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    note = EXCLUDED.note,
                    hash = EXCLUDED.hash,
                    scopes = EXCLUDED.scopes,
                    expires_at = EXCLUDED.expires_at
                """
            ),
            {
                "id": token_id,
                "name": name,
                "note": note,
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

    processed = 0
    with Session() as session:
        for raw, e in zip(raw_items, events):
            params = {
                "token_id": e.get("token_id"),
                "ts": (e.get("ts_ms", int(time.time() * 1000)) / 1000.0),
                "ip": e.get("ip"),
                "path": e.get("path"),
                "ua": e.get("ua"),
                "status": e.get("status"),
                "latency_ms": e.get("latency_ms"),
            }
            try:
                session.execute(
                    text(
                        """
                        INSERT INTO auth.api_token_usage (token_id, ts, ip, path, user_agent, status, latency_ms)
                        VALUES (:token_id, to_timestamp(:ts), :ip, :path, :ua, :status, :latency_ms)
                        """
                    ),
                    params,
                )
                session.flush()
            except IntegrityError:
                # Reset transaction state
                session.rollback()
                # Attempt to backfill missing token row from Redis meta, then retry once
                tid = e.get("token_id")
                if tid:
                    meta = redis_conn.hgetall(f"{API_TOKEN_META_PREFIX}{tid}")
                    if meta:
                        scopes = []
                        try:
                            scopes = json.loads(meta.get("scopes", "[]"))
                        except Exception:
                            scopes = []
                        session.execute(
                            text(
                                """
                                INSERT INTO auth.api_tokens (id, name, note, hash, scopes, expires_at)
                                VALUES (:id, :name, :note, :hash, :scopes,
                                        CASE WHEN :expires_ms > 0 THEN to_timestamp(:expires_ms / 1000.0)
                                             ELSE NULL END)
                                ON CONFLICT (id) DO NOTHING
                                """
                            ),
                            {
                                "id": tid,
                                "name": meta.get("name"),
                                "note": meta.get("note") or None,
                                "hash": meta.get("hash"),
                                "scopes": scopes,
                                "expires_ms": int(
                                    meta.get("expires_at_ms", 0) or 0
                                ),
                            },
                        )
                        # retry insert once
                        try:
                            session.execute(
                                text(
                                    """
                                    INSERT INTO auth.api_token_usage (token_id, ts, ip, path, user_agent, status, latency_ms)
                                    VALUES (:token_id, to_timestamp(:ts), :ip, :path, :ua, :status, :latency_ms)
                                    """
                                ),
                                params,
                            )
                            session.flush()
                        except IntegrityError:
                            session.rollback()
                            # Could not fix; requeue this event and continue
                            redis_conn.lrem(processing_key, 1, raw)
                            redis_conn.rpush(API_USAGE_QUEUE_KEY, raw)
                            continue
                    else:
                        # No meta; requeue
                        redis_conn.lrem(processing_key, 1, raw)
                        redis_conn.rpush(API_USAGE_QUEUE_KEY, raw)
                        continue
                else:
                    # No token id; requeue
                    redis_conn.lrem(processing_key, 1, raw)
                    redis_conn.rpush(API_USAGE_QUEUE_KEY, raw)
                    continue

            # Update counters after successful insert
            if e.get("token_id"):
                session.execute(
                    text(
                        "UPDATE auth.api_tokens SET last_used_at = NOW(), usage_count = usage_count + 1 WHERE id = :id"
                    ),
                    {"id": e.get("token_id")},
                )
            # Remove processed item from processing list and increment
            redis_conn.lrem(processing_key, 1, raw)
            processed += 1

        session.commit()
    return processed
