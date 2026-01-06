from __future__ import annotations

import logging
import time
from typing import Any, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared_lib.queries.ripple_queries import _schema

logger = logging.getLogger(__name__)


async def fetch_tournament_strength(
    session: AsyncSession,
    *,
    limit: int | None = None,
) -> tuple[Sequence[Mapping[str, Any]], int]:
    """
    Fetch tournaments ranked by strength.

    Strength is calculated as: ln(sum of top 20 player scores) / entrant_count

    Returns:
        - List of tournament dicts with keys:
          tournament_id, start_time_ms, entrant_count, top20_sum, strength
        - generated_at_ms timestamp
    """
    schema = _schema()
    schema_sql = f'"{schema}"'

    limit_clause = "" if limit is None else "LIMIT :limit_value"

    query_str = f"""
WITH latest_snapshot AS (
  SELECT MAX(calculated_at_ms) AS ts
  FROM {schema_sql}.player_rankings
),
tournament_scores AS (
  SELECT
    pat.tournament_id,
    pr.score,
    ROW_NUMBER() OVER (PARTITION BY pat.tournament_id ORDER BY pr.score DESC) AS rn
  FROM {schema_sql}.player_appearance_teams pat
  JOIN {schema_sql}.player_rankings pr ON pr.player_id = pat.player_id
  JOIN latest_snapshot ls ON pr.calculated_at_ms = ls.ts
),
tournament_stats AS (
  SELECT
    tournament_id,
    SUM(score) FILTER (WHERE rn <= 20) AS top20_sum,
    COUNT(*) AS entrant_count
  FROM tournament_scores
  GROUP BY tournament_id
)
SELECT
  t.tournament_id,
  t.name AS name,
  CASE
    WHEN t.start_time_ms < 1000000000000 THEN t.start_time_ms * 1000
    ELSE t.start_time_ms
  END AS start_time_ms,
  ts.entrant_count::int AS entrant_count,
  ts.top20_sum AS top20_sum,
  LN(GREATEST(ts.top20_sum, 1.0)) AS strength
FROM {schema_sql}.tournaments t
JOIN tournament_stats ts ON ts.tournament_id = t.tournament_id
WHERE t.is_ranked = TRUE
ORDER BY strength DESC
{limit_clause}
"""

    params: dict[str, Any] = {}
    if limit is not None:
        params["limit_value"] = limit

    result = await session.execute(text(query_str), params)
    rows = [dict(row._mapping) for row in result.fetchall()]

    generated_at_ms = int(time.time() * 1000)

    return rows, generated_at_ms
