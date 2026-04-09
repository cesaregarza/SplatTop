from __future__ import annotations

import base64
import logging
import os
import sqlite3
import threading
import time
import zlib
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator, Sequence

import orjson

import fast_api_app.connections as conn_mod
from shared_lib.constants import (
    LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY,
    LOOKUP_SQLITE_SNAPSHOT_META_KEY,
)
from shared_lib.monitoring import (
    LOOKUP_SQLITE_SNAPSHOT_EVENTS,
    LOOKUP_SQLITE_SNAPSHOT_RELOAD_DURATION,
    metrics_enabled,
)
from shared_lib.sqlite_lookup_snapshot import create_empty_lookup_snapshot

logger = logging.getLogger(__name__)


class SQLiteLookupSnapshotStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._version: str | None = None
        self._last_meta_poll = 0.0
        self._poll_interval_seconds = float(
            os.getenv("SQLITE_LOOKUP_SNAPSHOT_POLL_SECONDS", "5")
        )
        snapshot_dir = Path(
            os.getenv(
                "FASTAPI_SQLITE_SNAPSHOT_DIR",
                "/tmp/splattop-fastapi-lookups",
            )
        )
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_path = snapshot_dir / "lookup_snapshot.sqlite3"
        self._ensure_snapshot_exists()

    def _ensure_snapshot_exists(self) -> None:
        if self._snapshot_path.exists():
            return
        create_empty_lookup_snapshot(self._snapshot_path)

    def _should_poll(self, now: float) -> bool:
        return (now - self._last_meta_poll) >= self._poll_interval_seconds

    def refresh_if_needed(self, *, force: bool = False) -> None:
        self._ensure_snapshot_exists()
        started = perf_counter()
        now = time.monotonic()
        if not force and not self._should_poll(now):
            return

        with self._lock:
            now = time.monotonic()
            if not force and not self._should_poll(now):
                return
            self._last_meta_poll = now
            try:
                meta_raw = conn_mod.redis_conn.get(
                    LOOKUP_SQLITE_SNAPSHOT_META_KEY
                )
            except Exception as exc:
                if metrics_enabled():
                    LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                        action="reload",
                        outcome="meta_unavailable",
                    ).inc()
                    LOOKUP_SQLITE_SNAPSHOT_RELOAD_DURATION.labels(
                        outcome="meta_unavailable"
                    ).observe(perf_counter() - started)
                logger.warning(
                    "Lookup SQLite snapshot meta unavailable: %s",
                    exc,
                )
                return
            if meta_raw is None:
                if metrics_enabled():
                    LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                        action="reload",
                        outcome="meta_missing",
                    ).inc()
                return

            try:
                meta = orjson.loads(_coerce_bytes(meta_raw))
            except orjson.JSONDecodeError:
                if metrics_enabled():
                    LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                        action="reload",
                        outcome="meta_decode_error",
                    ).inc()
                    LOOKUP_SQLITE_SNAPSHOT_RELOAD_DURATION.labels(
                        outcome="meta_decode_error"
                    ).observe(perf_counter() - started)
                logger.warning("Failed to decode lookup SQLite snapshot meta")
                return

            version = str(meta.get("version") or "").strip()
            if not version or version == self._version:
                return

            try:
                blob_raw = conn_mod.redis_conn.get(
                    LOOKUP_SQLITE_SNAPSHOT_BLOB_KEY
                )
            except Exception as exc:
                if metrics_enabled():
                    LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                        action="reload",
                        outcome="blob_unavailable",
                    ).inc()
                    LOOKUP_SQLITE_SNAPSHOT_RELOAD_DURATION.labels(
                        outcome="blob_unavailable"
                    ).observe(perf_counter() - started)
                logger.warning(
                    "Lookup SQLite snapshot blob unavailable for %s: %s",
                    version,
                    exc,
                )
                return
            if blob_raw is None:
                if metrics_enabled():
                    LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                        action="reload",
                        outcome="blob_missing",
                    ).inc()
                    LOOKUP_SQLITE_SNAPSHOT_RELOAD_DURATION.labels(
                        outcome="blob_missing"
                    ).observe(perf_counter() - started)
                logger.warning("Lookup SQLite snapshot blob missing for %s", version)
                return

            try:
                compressed = base64.b64decode(_coerce_bytes(blob_raw))
                sqlite_bytes = zlib.decompress(compressed)
            except Exception:
                if metrics_enabled():
                    LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                        action="reload",
                        outcome="blob_decode_error",
                    ).inc()
                    LOOKUP_SQLITE_SNAPSHOT_RELOAD_DURATION.labels(
                        outcome="blob_decode_error"
                    ).observe(perf_counter() - started)
                logger.exception("Failed to decode lookup SQLite snapshot blob")
                return

            temp_path = self._snapshot_path.with_suffix(".sqlite3.tmp")
            temp_path.write_bytes(sqlite_bytes)
            os.replace(temp_path, self._snapshot_path)
            self._version = version
            if metrics_enabled():
                LOOKUP_SQLITE_SNAPSHOT_EVENTS.labels(
                    action="reload",
                    outcome="reloaded",
                ).inc()
                LOOKUP_SQLITE_SNAPSHOT_RELOAD_DURATION.labels(
                    outcome="reloaded"
                ).observe(perf_counter() - started)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.refresh_if_needed()
        connection = sqlite3.connect(
            f"file:{self._snapshot_path}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        try:
            yield connection
        finally:
            connection.close()


def _coerce_bytes(value: str | bytes) -> bytes:
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")


lookup_snapshot_store = SQLiteLookupSnapshotStore()


def prime_lookup_sqlite_snapshot() -> None:
    lookup_snapshot_store.refresh_if_needed(force=True)


def lookup_fetchall(
    query: str,
    params: Sequence[Any] | dict[str, Any] = (),
) -> list[tuple[Any, ...]]:
    with lookup_snapshot_store.connection() as connection:
        cursor = connection.execute(query, params)
        rows = cursor.fetchall()
    return [tuple(row) for row in rows]


def lookup_fetchall_with_columns(
    query: str,
    params: Sequence[Any] | dict[str, Any] = (),
) -> tuple[list[str], list[tuple[Any, ...]]]:
    with lookup_snapshot_store.connection() as connection:
        cursor = connection.execute(query, params)
        columns = [description[0] for description in cursor.description or []]
        rows = cursor.fetchall()
    return columns, [tuple(row) for row in rows]


def lookup_scalar(
    query: str,
    params: Sequence[Any] | dict[str, Any] = (),
) -> Any:
    with lookup_snapshot_store.connection() as connection:
        cursor = connection.execute(query, params)
        row = cursor.fetchone()
    if row is None:
        return None
    return row[0]
