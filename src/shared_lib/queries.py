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
SELECT *
FROM FilteredByTimestamp
WHERE mode = :mode
  AND region = :region
ORDER BY rank ASC;
"""

PLAYER_LATEST_QUERY = """
SELECT player_id, mode, timestamp
FROM xscraper.player_latest
WHERE player_id = :player_id;
"""
