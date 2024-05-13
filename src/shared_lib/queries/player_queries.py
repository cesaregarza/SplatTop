PLAYER_LATEST_QUERY = """
SELECT *
FROM xscraper.player_latest
WHERE player_id = :player_id;
"""

PLAYER_ALIAS_QUERY = """
SELECT splashtag, last_seen AS latest_updated_timestamp
FROM xscraper.aliases
WHERE player_id = :player_id
ORDER BY last_seen DESC;
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

PLAYER_DATA_QUERY = """
SELECT *
FROM xscraper.players
WHERE player_id = :player_id
"""

SEASON_RESULTS_QUERY = """
SELECT *
FROM xscraper.season_results
WHERE player_id = :player_id
"""
