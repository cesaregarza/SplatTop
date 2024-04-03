LEADERBOARD_MAIN_QUERY = """
WITH MaxTimestamp AS (
    SELECT MAX(timestamp) AS max_timestamp
    FROM xscraper.players
    WHERE mode = :mode
),
FilteredByTimestamp AS (
    SELECT *
    FROM xscraper.players
    WHERE timestamp = (SELECT max_timestamp FROM MaxTimestamp)
)
SELECT f.*, ps.region AS prev_season_region
FROM FilteredByTimestamp f
LEFT JOIN xscraper.player_season ps
  ON f.player_id = ps.player_id
  AND f.season_number - 1 = ps.season_number
WHERE f.mode = :mode
  AND f.region = :region
ORDER BY f.rank ASC;
"""

PLAYER_LATEST_QUERY = """
SELECT *
FROM xscraper.player_latest
WHERE player_id = :player_id;
"""

PLAYER_ALIAS_QUERY = """
SELECT splashtag, MAX(timestamp) AS latest_updated_timestamp
FROM (
    SELECT splashtag, timestamp
    FROM xscraper.players
    WHERE player_id = :player_id
      AND updated = TRUE
) AS filtered
GROUP BY splashtag;
"""

PLAYER_MOST_RECENT_ROW_QUERY = """
WITH LatestMode AS (
    SELECT mode
    FROM xscraper.player_latest
    WHERE player_id = :player_id
    ORDER BY last_updated DESC
    LIMIT 1
),
MostRecentRow AS (
    SELECT *
    FROM xscraper.players
    WHERE player_id = :player_id
      AND mode = (SELECT mode FROM LatestMode)
    ORDER BY timestamp DESC
    LIMIT 1
)
SELECT *
FROM MostRecentRow;
"""
