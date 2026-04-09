from __future__ import annotations

import base64
import hashlib
import logging
import tempfile
import time
import uuid
import zlib
from pathlib import Path
from time import perf_counter
from typing import Any

import orjson
import redis

from shared_lib.constants import (
    ALIASES_REDIS_KEY,
    LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY,
    LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY,
    LOOKUP_SQLITE_SNAPSHOT_META_KEY,
    REDIS_HOST,
    REDIS_PORT,
    SEASON_RESULTS_REDIS_KEY,
    WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
)
from shared_lib.monitoring import (
    LOOKUP_SQLITE_SNAPSHOT_BUILD_DURATION,
    LOOKUP_SQLITE_SNAPSHOT_BYTES,
    LOOKUP_SQLITE_SNAPSHOT_EVENTS,
    metrics_enabled,
)
from shared_lib.sqlite_lookup_snapshot import (
    LOOKUP_SNAPSHOT_SCHEMA_VERSION,
    create_lookup_snapshot_database,
    populate_lookup_snapshot_database,
)

logger = logging.getLogger(__name__)

_LOCK_TTL_SECONDS = 5 * 60

redis_conn = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
)


def _coerce_bytes(value: str | bytes | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")


def _load_json_value(key: str) -> tuple[Any, bytes]:
    raw = redis_conn.get(key)
    if raw is None:
        raise RuntimeError(f"Missing Redis payload for {key}")
    raw_bytes = _coerce_bytes(raw)
    try:
        return orjson.loads(raw_bytes), raw_bytes
    except orjson.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON payload for {key}") from exc


def _source_hash(raw_value: bytes) -> str:
    return hashlib.sha256(raw_value).hexdigest()


def _load_existing_meta() -> dict[str, Any] | None:
    raw = redis_conn.get(LOOKUP_SQLITE_SNAPSHOT_META_KEY)
    if raw is None:
        return None
    try:
        payload = orjson.loads(_coerce_bytes(raw))
    except orjson.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _find_missing_source_keys() -> list[str]:
    missing_keys: list[str] = []
    for key in (
        ALIASES_REDIS_KEY,
        WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
        SEASON_RESULTS_REDIS_KEY,
    ):
        if redis_conn.get(key) is None:
            missing_keys.append(key)
    return missing_keys


def refresh_lookup_sqlite_snapshot() -> dict[str, Any]:
    started = perf_counter()
    token = uuid.uuid4().hex
    if not redis_conn.set(
        LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY,
        token,
        nx=True,
        ex=_LOCK_TTL_SECONDS,
    ):
        if metrics_enabled():
            LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                action="build",
                outcome="lock_missed",
            ).inc()
            LOOKUP_SQLITE_SNAPSHOT_BUILD_DURATION.labels(
                outcome="lock_missed"
            ).observe(perf_counter() - started)
        return {"rebuilt": False, "reason": "lock_missed"}

    try:
        missing_keys = _find_missing_source_keys()
        if missing_keys:
            if metrics_enabled():
                LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                    action="build",
                    outcome="source_missing",
                ).inc()
                LOOKUP_SQLITE_SNAPSHOT_BUILD_DURATION.labels(
                    outcome="source_missing"
                ).observe(perf_counter() - started)
            logger.info(
                "Skipping lookup SQLite snapshot build; missing source keys: %s",
                ", ".join(missing_keys),
            )
            return {
                "rebuilt": False,
                "reason": "source_missing",
                "missing_keys": missing_keys,
            }

        aliases, aliases_raw = _load_json_value(ALIASES_REDIS_KEY)
        weapon_rows, weapon_raw = _load_json_value(
            WEAPON_LEADERBOARD_PEAK_REDIS_KEY
        )
        season_rows, season_raw = _load_json_value(SEASON_RESULTS_REDIS_KEY)

        if not isinstance(aliases, list):
            raise RuntimeError("Alias payload is not a list")
        if not isinstance(weapon_rows, list):
            raise RuntimeError("Weapon leaderboard payload is not a list")
        if not isinstance(season_rows, list):
            raise RuntimeError("Season results payload is not a list")

        source_hashes = {
            "aliases": _source_hash(aliases_raw),
            "weapon_leaderboard_peak": _source_hash(weapon_raw),
            "season_results": _source_hash(season_raw),
        }

        existing_meta = _load_existing_meta() or {}
        if (
            existing_meta.get("schema_version")
            == LOOKUP_SNAPSHOT_SCHEMA_VERSION
            and existing_meta.get("source_hashes") == source_hashes
        ):
            if metrics_enabled():
                LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                    action="build",
                    outcome="skipped",
                ).inc()
                LOOKUP_SQLITE_SNAPSHOT_BUILD_DURATION.labels(
                    outcome="skipped"
                ).observe(perf_counter() - started)
            return {
                "rebuilt": False,
                "reason": "unchanged",
                "version": existing_meta.get("version"),
            }

        with tempfile.TemporaryDirectory(
            prefix="splattop-lookup-sqlite-"
        ) as temp_dir:
            db_path = Path(temp_dir) / "lookup_snapshot.sqlite3"
            connection = create_lookup_snapshot_database(db_path)
            try:
                row_counts = populate_lookup_snapshot_database(
                    connection,
                    aliases=aliases,
                    weapon_rows=weapon_rows,
                    season_rows=season_rows,
                )
            finally:
                connection.close()

            db_bytes = db_path.read_bytes()

        compressed = zlib.compress(db_bytes, level=6)
        encoded_blob = base64.b64encode(compressed).decode("ascii")
        built_at_ms = int(time.time() * 1000)
        version = f"{built_at_ms}-{uuid.uuid4().hex[:8]}"
        meta = {
            "version": version,
            "schema_version": LOOKUP_SNAPSHOT_SCHEMA_VERSION,
            "built_at_ms": built_at_ms,
            "compression": "zlib",
            "encoding": "base64",
            "row_counts": row_counts,
            "source_hashes": source_hashes,
            "bytes": {
                "sqlite": len(db_bytes),
                "compressed": len(compressed),
                "encoded": len(encoded_blob),
            },
        }

        redis_conn.set(LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY, encoded_blob)
        redis_conn.set(
            LOOKUP_SQLITE_SNAPSHOT_META_KEY,
            orjson.dumps(meta),
        )
        if metrics_enabled():
            LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                action="build",
                outcome="published",
            ).inc()
            LOOKUP_SQLITE_SNAPSHOT_BUILD_DURATION.labels(
                outcome="published"
            ).observe(perf_counter() - started)
            LOOKUP_SQLITE_SNAPSHOT_BYTES.labels(kind="sqlite").set(
                float(len(db_bytes))
            )
            LOOKUP_SQLITE_SNAPSHOT_BYTES.labels(kind="compressed").set(
                float(len(compressed))
            )
            LOOKUP_SQLITE_SNAPSHOT_BYTES.labels(kind="encoded").set(
                float(len(encoded_blob))
            )
        return {
            "rebuilt": True,
            "version": version,
            "row_counts": row_counts,
            "bytes": meta["bytes"],
        }
    except Exception:
        if metrics_enabled():
            LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                action="build",
                outcome="error",
            ).inc()
            LOOKUP_SQLITE_SNAPSHOT_BUILD_DURATION.labels(
                outcome="error"
            ).observe(perf_counter() - started)
        logger.exception("Failed to refresh lookup SQLite snapshot")
        raise
    finally:
        try:
            if redis_conn.get(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY) == token:
                redis_conn.delete(LOOKUP_SQLITE_SNAPSHOT_LOCK_KEY)
        except Exception:
            logger.debug("Failed to release lookup SQLite snapshot lock")
