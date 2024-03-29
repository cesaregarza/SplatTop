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
