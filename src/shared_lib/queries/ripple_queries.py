from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

import logging
import re
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _schema() -> str:
    """Return a validated schema name from env.

    Uses env RANKINGS_DB_SCHEMA, defaults to 'rankings'. Falls back to
    'rankings' if validation fails.
    """
    import os

    candidate = os.getenv("RANKINGS_DB_SCHEMA", "rankings")
    if _SCHEMA_RE.match(candidate):
        return candidate
    logger.warning(
        "Invalid RANKINGS_DB_SCHEMA '%s'; falling back to 'rankings'",
        candidate,
    )
    return "rankings"


async def fetch_ripple_page(
    session: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
    min_tournaments: Optional[int] = 3,
    tournament_window_days: int = 90,
    ranked_only: bool = True,
    build: Optional[str] = None,
    ts_ms: Optional[int] = None,
) -> tuple[list[Mapping[str, Any]], int, Optional[int], Optional[str]]:
    """Fetch a page of ripple rankings with total count and run metadata.

    Returns: (rows, total_count, calculated_at_ms, build_version)
    """

    schema = _schema()

    cte = f"""
    WITH latest_ts AS (
      SELECT CASE
        WHEN CAST(:ts_param AS BIGINT) IS NOT NULL THEN CAST(:ts_param AS BIGINT)
        WHEN CAST(:build_param AS TEXT) IS NOT NULL THEN (
          SELECT MAX(calculated_at_ms)
          FROM {schema}.player_rankings
          WHERE build_version = CAST(:build_param AS TEXT)
        )
        ELSE (
          SELECT MAX(calculated_at_ms) FROM {schema}.player_rankings
        )
      END AS ts
    ), tournament_times AS (
      SELECT
        t.tournament_id,
        CASE WHEN t.start_time_ms < 1000000000000 THEN t.start_time_ms * 1000 ELSE t.start_time_ms END AS start_ms,
        CASE
          WHEN MAX(m.last_game_finished_at_ms) IS NULL THEN NULL
          WHEN MAX(m.last_game_finished_at_ms) < 1000000000000 THEN MAX(m.last_game_finished_at_ms) * 1000
          ELSE MAX(m.last_game_finished_at_ms)
        END AS end_ms,
        t.is_ranked
      FROM {schema}.tournaments t
      LEFT JOIN {schema}.matches m ON m.tournament_id = t.tournament_id
      GROUP BY t.tournament_id, t.start_time_ms, t.is_ranked
    ), normalized AS (
      SELECT
        pat.player_id,
        pat.tournament_id,
        COALESCE(tt.end_ms, tt.start_ms) AS event_ms,
        tt.is_ranked
      FROM {schema}.player_appearance_teams pat
      JOIN tournament_times tt ON tt.tournament_id = pat.tournament_id
    ), ranked AS (
      SELECT
        r.player_id,
        r.score,
        r.win_pr,
        r.loss_pr,
        r.exposure,
        r.calculated_at_ms,
        r.build_version,
        p.display_name,
        s.tournament_count,
        s.last_active_ms,
        (
          SELECT COUNT(DISTINCT n.tournament_id)
          FROM normalized n
          JOIN latest_ts l2 ON TRUE
          WHERE n.player_id = r.player_id
            AND n.event_ms BETWEEN (l2.ts - CAST(:window_ms AS BIGINT)) AND l2.ts
            AND (:ranked_only = false OR n.is_ranked IS TRUE)
        ) AS window_count,
        ROW_NUMBER() OVER (ORDER BY r.score DESC) AS rank
      FROM {schema}.player_rankings r
      JOIN latest_ts l ON r.calculated_at_ms = l.ts
      LEFT JOIN {schema}.player_ranking_stats s
        ON s.player_id = r.player_id AND s.calculated_at_ms = r.calculated_at_ms AND s.build_version = r.build_version
      LEFT JOIN {schema}.players p ON p.player_id = r.player_id
      WHERE (
        CAST(:min_tournaments AS INT) IS NULL
        OR (
          SELECT COUNT(DISTINCT n2.tournament_id)
          FROM normalized n2
          JOIN latest_ts l3 ON TRUE
          WHERE n2.player_id = r.player_id
            AND n2.event_ms BETWEEN (l3.ts - CAST(:window_ms AS BIGINT)) AND l3.ts
            AND (:ranked_only = false OR n2.is_ranked IS TRUE)
        ) >= CAST(:min_tournaments AS INT)
      )
    )
    """

    page_sql = text(
        cte
        + """
    SELECT *
    FROM ranked
    ORDER BY score DESC
    LIMIT :limit OFFSET :offset
    """
    )

    count_sql = text(
        cte
        + """
    SELECT COUNT(*)::int AS total,
           MAX(calculated_at_ms)::bigint AS calculated_at_ms,
           MAX(build_version)::text AS build_version
    FROM ranked
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
    rows: Sequence[Mapping[str, Any]] = page_res.mappings().all()

    count_res = await session.execute(count_sql, params)
    count_row = count_res.mappings().one()
    total = int(count_row.get("total", 0))
    calc_ts = count_row.get("calculated_at_ms")
    build_version = count_row.get("build_version")

    return list(rows), total, calc_ts, build_version


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

    ctes = f"""
WITH latest_ts AS NOT MATERIALIZED (
  SELECT CASE
    WHEN CAST(:ts_param AS BIGINT) IS NOT NULL THEN CAST(:ts_param AS BIGINT)
    WHEN CAST(:build_param AS TEXT) IS NOT NULL THEN (
      SELECT MAX(calculated_at_ms)
      FROM {schema}.player_rankings
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
  FROM {schema}.tournaments t
  LEFT JOIN {schema}.matches m ON m.tournament_id = t.tournament_id
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
  JOIN {schema}.player_appearance_teams pat ON pat.tournament_id = tw.tournament_id
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
LEFT JOIN {schema}.players p ON p.player_id = a.player_id
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
