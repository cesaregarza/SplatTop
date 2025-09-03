from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _schema() -> str:
    """Return the rankings schema name (env RANKINGS_DB_SCHEMA or 'rankings')."""
    import os

    return os.getenv("RANKINGS_DB_SCHEMA", "rankings")


async def fetch_ripple_page(
    session: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
    min_tournaments: Optional[int] = 3,
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
        WHEN :ts_param::bigint IS NOT NULL THEN :ts_param::bigint
        WHEN :build_param::text IS NOT NULL THEN (
          SELECT MAX(calculated_at_ms) FROM {schema}.player_rankings WHERE build_version = :build_param
        )
        ELSE (
          SELECT MAX(calculated_at_ms) FROM {schema}.player_rankings
        )
      END AS ts
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
        ROW_NUMBER() OVER (ORDER BY r.score DESC) AS rank
      FROM {schema}.player_rankings r
      JOIN latest_ts l ON r.calculated_at_ms = l.ts
      LEFT JOIN {schema}.player_ranking_stats s
        ON s.player_id = r.player_id AND s.calculated_at_ms = r.calculated_at_ms AND s.build_version = r.build_version
      LEFT JOIN {schema}.players p ON p.player_id = r.player_id
      WHERE (:min_tournaments IS NULL OR COALESCE(s.tournament_count, 0) >= :min_tournaments)
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
