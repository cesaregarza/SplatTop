from __future__ import annotations

import logging
import re
from typing import Any, Mapping, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _schema() -> str:
    """Return a validated schema name from env.

    Uses env RANKINGS_DB_SCHEMA, defaults to 'comp_rankings'. Falls back to
    'rankings' if validation fails.
    """
    import os

    candidate = os.getenv("RANKINGS_DB_SCHEMA", "comp_rankings")
    if _SCHEMA_RE.match(candidate):
        return candidate
    logger.warning(
        "Invalid RANKINGS_DB_SCHEMA '%s'; falling back to 'comp_rankings'",
        candidate,
    )
    return "comp_rankings"


async def fetch_ripple_page(
    session: "AsyncSession",
    *,
    limit: int = 100,
    offset: int = 0,
    min_tournaments: Optional[int] = 3,
    tournament_window_days: int = 90,
    ranked_only: bool = True,
    build: Optional[str] = None,
    ts_ms: Optional[int] = None,
) -> tuple[list[Mapping[str, Any]], int, Optional[int], Optional[str]]:
    """
    Faster Ripple page using the tournament_event_times MV.
    - 1 SQL round-trip (COUNT(*) OVER()).
    - No correlated subqueries for window counts.
    - No DB ROW_NUMBER(); page rank computed client-side.
    - Never references the 'rank' identifier from player_rankings.
    """

    schema = _schema()
    schema_sql = f'"{schema}"'  # safe quoting, schema name validated upstream

    # Compute once in Python (no risk of int overflow here; Python ints are unbounded).
    window_ms = int(tournament_window_days) * 86_400_000

    sql = text(
        f"""
WITH latest_ts AS (
  SELECT CASE
    WHEN CAST(:ts_param AS BIGINT) IS NOT NULL THEN CAST(:ts_param AS BIGINT)
    WHEN CAST(:build_param AS TEXT) IS NOT NULL THEN (
      SELECT MAX(calculated_at_ms)
      FROM {schema_sql}.player_rankings
      WHERE build_version = CAST(:build_param AS TEXT)
    )
    ELSE (SELECT MAX(calculated_at_ms) FROM {schema_sql}.player_rankings)
  END AS ts
),
-- rankings snapshot at ts (avoid the 'rank' column entirely)
r_latest AS (
  SELECT r.player_id, r.score, r.win_pr, r.loss_pr, r.exposure,
         r.calculated_at_ms, r.build_version
  FROM {schema_sql}.player_rankings r
  JOIN latest_ts l ON r.calculated_at_ms = l.ts
),
-- MV-powered window selection (fast)
tt_window AS (
  SELECT t.tournament_id, t.event_ms
  FROM {schema_sql}.tournament_event_times t
  JOIN latest_ts l ON TRUE
  WHERE t.event_ms BETWEEN (l.ts - :window_ms::bigint) AND l.ts
    AND (:ranked_only::boolean = FALSE OR t.is_ranked IS TRUE)
),
-- touch appearances only for tournaments in the window and players in the snapshot
events_in_window AS (
  SELECT DISTINCT pat.player_id, w.tournament_id
  FROM {schema_sql}.player_appearance_teams pat
  JOIN tt_window w       ON w.tournament_id = pat.tournament_id
  JOIN r_latest rl       ON rl.player_id    = pat.player_id
),
-- compute per-player window_count once
window_counts AS (
  SELECT e.player_id, COUNT(*)::int AS window_count
  FROM events_in_window e
  GROUP BY e.player_id
),
-- if min_tournaments is provided, filter here (NULL => no filter)
eligible AS (
  SELECT rl.player_id
  FROM r_latest rl
  LEFT JOIN window_counts wc ON wc.player_id = rl.player_id
  WHERE (:min_tournaments IS NULL OR COALESCE(wc.window_count, 0) >= :min_tournaments::int)
),
-- assemble paged rows
base AS (
  SELECT
    rl.player_id, rl.score, rl.win_pr, rl.loss_pr, rl.exposure,
    rl.calculated_at_ms, rl.build_version,
    p.display_name,
    s.tournament_count, s.last_active_ms,
    COALESCE(wc.window_count, 0) AS window_count
  FROM eligible e
  JOIN r_latest rl ON rl.player_id = e.player_id
  LEFT JOIN window_counts wc ON wc.player_id = rl.player_id
  LEFT JOIN {schema_sql}.player_ranking_stats s
    ON s.player_id = rl.player_id
   AND s.calculated_at_ms = rl.calculated_at_ms
   AND s.build_version    = rl.build_version
  LEFT JOIN {schema_sql}.players p ON p.player_id = rl.player_id
)
SELECT
  base.*,
  COUNT(*) OVER () AS __total
FROM base
ORDER BY score DESC, player_id  -- deterministic for client-side rank
LIMIT :limit::int OFFSET :offset::int
"""
    )

    params = {
        "limit": int(limit),
        "offset": int(offset),
        "min_tournaments": min_tournaments,
        "window_ms": int(window_ms),
        "ranked_only": bool(ranked_only),
        "build_param": build,
        "ts_param": ts_ms,
    }

    res = await session.execute(sql, params)
    rows: Sequence[Mapping[str, Any]] = res.mappings().all()

    if rows:
        total = int(rows[0]["__total"])
        calc_ts = rows[0]["calculated_at_ms"]
        build_version = rows[0]["build_version"]
    else:
        # No rows matched the filter; fetch run metadata cheaply
        meta_sql = text(
            f"""
        WITH latest_ts AS (
          SELECT CASE
            WHEN CAST(:ts_param AS BIGINT) IS NOT NULL THEN CAST(:ts_param AS BIGINT)
            WHEN CAST(:build_param AS TEXT) IS NOT NULL THEN (
              SELECT MAX(calculated_at_ms)
              FROM {schema_sql}.player_rankings
              WHERE build_version = CAST(:build_param AS TEXT)
            )
            ELSE (SELECT MAX(calculated_at_ms) FROM {schema_sql}.player_rankings)
          END AS ts
        )
        SELECT l.ts AS calculated_at_ms,
               (SELECT MAX(build_version)::text
                  FROM {schema_sql}.player_rankings r
                  JOIN latest_ts l ON r.calculated_at_ms = l.ts) AS build_version
        FROM latest_ts l
        """
        )
        meta = (await session.execute(meta_sql, params)).mappings().one()
        total = 0
        calc_ts = meta["calculated_at_ms"]
        build_version = meta["build_version"]

    # Build output rows, drop __total, and compute the page rank client-side
    out_rows: list[dict] = []
    for i, r in enumerate(rows):
        row = dict(r)
        row.pop("__total", None)
        row["rank"] = offset + i + 1
        out_rows.append(row)

    return out_rows, total, calc_ts, build_version


async def fetch_ripple_danger(
    session: AsyncSession,
    *,
    limit: int = 20,
    offset: int = 0,
    min_tournaments: Optional[int] = None,
    tournament_window_days: int = 90,
    ranked_only: bool = True,
    build: Optional[str] = None,
    ts_ms: Optional[int] = None,
) -> tuple[list[Mapping[str, Any]], int, Optional[int], Optional[str]]:
    """Optimized 'danger' query (top‑k lateral semantics via NOT MATERIALIZED CTEs).

    Returns rows with player_rank, player_id, display_name, score,
    oldest_in_window_ms, next_expiry_ms, ms_left, calculated_at_ms, build_version.
    """

    schema = _schema()
    schema_sql = f'"{schema}"'

    ctes = f"""
WITH latest_ts AS NOT MATERIALIZED (
  SELECT CASE
    WHEN CAST(:ts_param AS BIGINT) IS NOT NULL THEN CAST(:ts_param AS BIGINT)
    WHEN CAST(:build_param AS TEXT) IS NOT NULL THEN (
      SELECT MAX(calculated_at_ms)
      FROM {schema_sql}.player_rankings
      WHERE build_version = CAST(:build_param AS TEXT)
    )
    ELSE (SELECT MAX(calculated_at_ms) FROM {schema}.player_rankings)
  END AS ts
),
r_ranked AS NOT MATERIALIZED (
  SELECT r.player_id,
         r.score,
         r.build_version,
         ROW_NUMBER() OVER (ORDER BY r.score DESC) AS player_rank
  FROM {schema}.player_rankings r
  JOIN latest_ts l ON r.calculated_at_ms = l.ts
),
tournament_times AS NOT MATERIALIZED (
  SELECT
    t.tournament_id,
    CASE WHEN t.start_time_ms < 1000000000000 THEN t.start_time_ms * 1000 ELSE t.start_time_ms END AS start_ms,
    CASE
      WHEN MAX(m.last_game_finished_at_ms) IS NULL THEN NULL
      WHEN MAX(m.last_game_finished_at_ms) < 1000000000000 THEN MAX(m.last_game_finished_at_ms) * 1000
      ELSE MAX(m.last_game_finished_at_ms)
    END AS end_ms,
    t.is_ranked
  FROM {schema_sql}.tournaments t
  LEFT JOIN {schema_sql}.matches m ON m.tournament_id = t.tournament_id
  GROUP BY t.tournament_id, t.start_time_ms, t.is_ranked
),
tt_window AS NOT MATERIALIZED (
  SELECT tt.tournament_id,
         COALESCE(tt.end_ms, tt.start_ms) AS event_ms,
         tt.is_ranked
  FROM tournament_times tt
  JOIN latest_ts l ON TRUE
  WHERE COALESCE(tt.end_ms, tt.start_ms) BETWEEN (l.ts - CAST(:window_ms AS BIGINT)) AND l.ts
    AND (:ranked_only = false OR tt.is_ranked IS TRUE)
),
pt_win AS NOT MATERIALIZED (
  SELECT DISTINCT pat.player_id,
                  tw.tournament_id,
                  tw.event_ms
  FROM tt_window tw
  JOIN {schema_sql}.player_appearance_teams pat ON pat.tournament_id = tw.tournament_id
  JOIN r_ranked rr ON rr.player_id = pat.player_id
),
agg AS NOT MATERIALIZED (
  SELECT player_id,
         COUNT(*)::int AS n_tournaments,
         MIN(event_ms) AS oldest_in_window_ms
  FROM pt_win
  GROUP BY player_id
)
    """

    page_sql = text(
        ctes
        + f"""
SELECT rr.player_rank,
       a.player_id,
       p.display_name,
       rr.score,
       a.oldest_in_window_ms,
       (a.oldest_in_window_ms + CAST(:window_ms AS BIGINT)) AS next_expiry_ms,
       (a.oldest_in_window_ms + CAST(:window_ms AS BIGINT)) - l.ts AS ms_left,
       a.n_tournaments AS window_count,
       l.ts AS calculated_at_ms,
       rr.build_version
FROM agg a
JOIN latest_ts l ON TRUE
JOIN r_ranked rr ON rr.player_id = a.player_id
LEFT JOIN {schema_sql}.players p ON p.player_id = a.player_id
WHERE (CAST(:min_tournaments AS INT) IS NULL OR a.n_tournaments = CAST(:min_tournaments AS INT))
ORDER BY ms_left ASC, rr.player_rank ASC
LIMIT :limit OFFSET :offset
        """
    )

    count_sql = text(
        ctes
        + """
SELECT COUNT(*)::int AS total,
       MAX(l.ts)::bigint AS calculated_at_ms
FROM agg a
JOIN latest_ts l ON TRUE
WHERE (CAST(:min_tournaments AS INT) IS NULL OR a.n_tournaments = CAST(:min_tournaments AS INT))
        """
    )

    params = {
        "limit": int(limit),
        "offset": int(offset),
        "min_tournaments": min_tournaments,
        "window_ms": int(tournament_window_days) * 86400000,
        "ranked_only": bool(ranked_only),
        "build_param": build,
        "ts_param": ts_ms,
    }

    page_res = await session.execute(page_sql, params)
    rows = page_res.mappings().all()

    count_res = await session.execute(count_sql, params)
    count_row = count_res.mappings().one()
    total = int(count_row.get("total", 0))
    calc_ts = count_row.get("calculated_at_ms")
    build_version = None
    if rows:
        build_version = rows[0].get("build_version")
    return list(rows), total, calc_ts, build_version
