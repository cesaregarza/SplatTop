from __future__ import annotations

import json
import logging
import time
from time import perf_counter
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from celery_app.connections import Session, redis_conn
from shared_lib.constants import (
    API_TOKEN_META_PREFIX,
    API_USAGE_LOCK_KEY,
    API_USAGE_PROCESSING_KEY,
    API_USAGE_QUEUE_KEY,
)
from shared_lib.monitoring import (
    API_USAGE_BATCH_DURATION,
    API_USAGE_EVENTS,
    API_USAGE_RECOVERED,
    metrics_enabled,
)

logger = logging.getLogger(__name__)


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
    """Flush usage events with a Redis processing list and a simple lock.

    - Acquires a short-lived Redis lock to prevent overlapping workers.
    - Recovers orphaned items from the processing list (previous crash).
    - Uses RPOPLPUSH to move items atomically to processing while handling
      malformed JSON and DB errors. Permanently failing events are routed to
      a dead-letter queue after a small number of attempts.
    """
    import os

    _ensure_schema()
    processed = 0
    bs = batch_size or int(os.getenv("API_USAGE_FLUSH_BATCH", "1000"))
    processing_key = API_USAGE_PROCESSING_KEY
    dlq_key = f"{API_USAGE_QUEUE_KEY}:dlq"
    max_attempts = int(os.getenv("API_USAGE_MAX_ATTEMPTS", "5"))
    # Lock TTL: default 55s. Consider increasing for larger batch sizes or
    # slower databases; keep configurable via env.
    lock_ttl = int(os.getenv("API_USAGE_LOCK_TTL", "55"))
    lock_key = API_USAGE_LOCK_KEY
    worker_id = f"worker:{int(time.time()*1000)}"
    batch_start = perf_counter()

    # Acquire lock to avoid overlapping flushers
    if not redis_conn.set(lock_key, worker_id, nx=True, ex=lock_ttl):
        if metrics_enabled():
            API_USAGE_EVENTS.labels(result="lock_missed").inc()
            API_USAGE_BATCH_DURATION.observe(perf_counter() - batch_start)
        return 0

    try:
        # Recover any orphaned items left in processing (previous crash)
        try:
            # Recover at most N orphaned items per run to avoid long loops
            recover_limit = int(os.getenv("API_USAGE_RECOVER_LIMIT", "1000"))
            recovered = 0
            while recovered < recover_limit:
                orphan = redis_conn.rpop(processing_key)
                if orphan is None:
                    break
                redis_conn.lpush(API_USAGE_QUEUE_KEY, orphan)
                recovered += 1
                if metrics_enabled():
                    API_USAGE_RECOVERED.inc()
        except Exception as e:
            # Best-effort recovery; log and continue for visibility
            logger.warning("Processing-list orphan recovery failed: %s", e)

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
                # Malformed JSON -> move to DLQ and drop from processing
                logger.warning("Malformed usage event; sending to DLQ")
                redis_conn.lrem(processing_key, 1, item)
                redis_conn.lpush(dlq_key, item)
                if metrics_enabled():
                    API_USAGE_EVENTS.labels(result="malformed").inc()
                    API_USAGE_EVENTS.labels(result="dlq").inc()
                # Remove last raw to keep alignment with events
                try:
                    raw_items.pop()
                except Exception:
                    pass
                continue

        if not events:
            if metrics_enabled():
                API_USAGE_EVENTS.labels(result="empty").inc()
                API_USAGE_BATCH_DURATION.observe(perf_counter() - batch_start)
            return 0
        with Session() as session:
            ack_items: List[str] = []
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
                        meta = redis_conn.hgetall(
                            f"{API_TOKEN_META_PREFIX}{tid}"
                        )
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
                                # Could not fix; requeue with attempts or DLQ
                                attempts = int(e.get("attempts", 0)) + 1
                                e["attempts"] = attempts
                                redis_conn.lrem(processing_key, 1, raw)
                                if attempts >= max_attempts:
                                    logger.warning(
                                        "Usage event moved to DLQ after max attempts"
                                    )
                                    redis_conn.lpush(dlq_key, json.dumps(e))
                                    if metrics_enabled():
                                        API_USAGE_EVENTS.labels(result="dlq").inc()
                                else:
                                    redis_conn.rpush(
                                        API_USAGE_QUEUE_KEY, json.dumps(e)
                                    )
                                    if metrics_enabled():
                                        API_USAGE_EVENTS.labels(
                                            result="requeued"
                                        ).inc()
                                continue
                        else:
                            # No meta; requeue with attempts or DLQ
                            attempts = int(e.get("attempts", 0)) + 1
                            e["attempts"] = attempts
                            redis_conn.lrem(processing_key, 1, raw)
                            if attempts >= max_attempts:
                                logger.warning(
                                    "Usage event moved to DLQ (no meta)"
                                )
                                redis_conn.lpush(dlq_key, json.dumps(e))
                                if metrics_enabled():
                                    API_USAGE_EVENTS.labels(result="dlq").inc()
                            else:
                                redis_conn.rpush(
                                    API_USAGE_QUEUE_KEY, json.dumps(e)
                                )
                                if metrics_enabled():
                                    API_USAGE_EVENTS.labels(result="requeued").inc()
                            continue
                    else:
                        # No token id; requeue with attempts or DLQ
                        attempts = int(e.get("attempts", 0)) + 1
                        e["attempts"] = attempts
                        redis_conn.lrem(processing_key, 1, raw)
                        if attempts >= max_attempts:
                            logger.warning(
                                "Usage event moved to DLQ (no token_id)"
                            )
                            redis_conn.lpush(dlq_key, json.dumps(e))
                            if metrics_enabled():
                                API_USAGE_EVENTS.labels(result="dlq").inc()
                        else:
                            redis_conn.rpush(API_USAGE_QUEUE_KEY, json.dumps(e))
                            if metrics_enabled():
                                API_USAGE_EVENTS.labels(result="requeued").inc()
                        continue

                # Update counters after successful insert
                if e.get("token_id"):
                    session.execute(
                        text(
                            "UPDATE auth.api_tokens SET last_used_at = NOW(), usage_count = usage_count + 1 WHERE id = :id"
                        ),
                        {"id": e.get("token_id")},
                    )
                ack_items.append(raw)

            try:
                session.commit()
            except Exception as exc:
                session.rollback()
                logger.error("Failed to commit API usage batch: %s", exc)
                if metrics_enabled():
                    API_USAGE_EVENTS.labels(result="db_error").inc()
                    API_USAGE_BATCH_DURATION.observe(
                        perf_counter() - batch_start
                    )
                return processed

            acked = 0
            for raw in ack_items:
                try:
                    removed = redis_conn.lrem(processing_key, 1, raw)
                    if removed:
                        acked += int(removed)
                except Exception as ack_exc:
                    logger.warning(
                        "Failed to ack usage event from processing: %s", ack_exc
                    )
            if metrics_enabled() and acked:
                API_USAGE_EVENTS.labels(result="processed").inc(acked)
            processed += acked
    finally:
        # Release lock if we still own it
        try:
            val = redis_conn.get(lock_key)
            if val == worker_id:
                redis_conn.delete(lock_key)
        except Exception:
            pass
    if metrics_enabled():
        API_USAGE_BATCH_DURATION.observe(perf_counter() - batch_start)
    return processed
