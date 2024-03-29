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
SELECT player_id, timestamp, mode
FROM (
    SELECT 
        player_id, 
        mode, 
        timestamp, 
        season_number,
        ROW_NUMBER() OVER (
            PARTITION BY player_id, mode 
            ORDER BY timestamp DESC, season_number DESC
        ) AS rn
    FROM xscraper.players
    WHERE player_id = :player_id
) AS subquery
WHERE rn = 1;
"""
