CURRENT_SEASON_QUERY = """
SELECT MAX(season_number) AS season_number
FROM xscraper.players;
"""

PLAYER_LATEST_QUERY = """
SELECT *
FROM xscraper.player_latest
WHERE player_id = :player_id;
"""

PLAYER_LATEST_DATA_QUERY = """
SELECT
    p.mode,
    p.region,
    p.season_number,
    p.rank,
    p.x_power,
    p.weapon_id
FROM xscraper.player_latest pl
JOIN xscraper.players p
    ON p.player_id = pl.player_id
    AND p.mode = pl.mode
    AND p.timestamp = pl.timestamp
WHERE pl.player_id = :player_id
ORDER BY p.mode ASC;
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
SELECT
    mode,
    region,
    season_number,
    timestamp,
    x_power,
    weapon_id,
    rank,
    updated
FROM xscraper.players
WHERE player_id = :player_id
ORDER BY timestamp ASC
"""

SEASON_RESULTS_QUERY = """
SELECT
    mode,
    region,
    season_number,
    rank,
    x_power,
    weapon_id
FROM xscraper.season_results
WHERE player_id = :player_id
ORDER BY season_number DESC, mode ASC
"""
