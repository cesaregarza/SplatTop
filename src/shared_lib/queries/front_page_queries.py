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
),
GoldSilverCounts AS (
    SELECT 
        player_id,
        COUNT(CASE WHEN rank <= 10 THEN 1 END) AS gold_x_count,
        COUNT(CASE WHEN rank > 10 THEN 1 END) AS silver_x_count
    FROM xscraper.season_results
    GROUP BY player_id
),
DiamondCounts AS (
    SELECT 
        player_id,
        COUNT(*) AS diamond_x_count
    FROM (
        SELECT player_id, season_number, COUNT(CASE WHEN rank <= 10 THEN 1 END) AS top_10_finishes
        FROM xscraper.season_results
        GROUP BY player_id, season_number
        HAVING COUNT(CASE WHEN rank <= 10 THEN 1 END) >= 4
    ) AS QualifiedSeasons
    GROUP BY player_id
)
SELECT 
    f.*, 
    ps.region AS prev_season_region,
    COALESCE(gsc.gold_x_count, 0) AS gold_x_count,
    COALESCE(gsc.silver_x_count, 0) AS silver_x_count,
    COALESCE(dc.diamond_x_count, 0) AS diamond_x_count
FROM FilteredByTimestamp f
LEFT JOIN xscraper.player_season ps
    ON f.player_id = ps.player_id
    AND f.season_number - 1 = ps.season_number
LEFT JOIN GoldSilverCounts gsc
    ON f.player_id = gsc.player_id
LEFT JOIN DiamondCounts dc
    ON f.player_id = dc.player_id
WHERE f.mode = :mode
    AND f.region = :region
ORDER BY f.rank ASC;
"""

RACE_TO_5000_CURRENT_QUERY = """
WITH current_season AS (
    SELECT MAX(season_number) AS season_number
    FROM xscraper.players
),
ranked_points AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.player_id, p.season_number, p.mode, p.region
            ORDER BY p.timestamp DESC
        ) AS row_num
    FROM xscraper.players p
    JOIN current_season cs
        ON p.season_number = cs.season_number
    WHERE p.updated
),
qualifying_runs AS (
    SELECT
        rp.player_id,
        rp.season_number,
        rp.mode,
        rp.region
    FROM ranked_points rp
    WHERE rp.row_num = 1
        AND rp.x_power >= :threshold
)
SELECT
    p.player_id,
    p.splashtag,
    p.rank,
    p.x_power,
    p.timestamp,
    p.mode,
    p.region,
    p.season_number
FROM xscraper.players p
JOIN qualifying_runs q
    ON p.player_id = q.player_id
    AND p.season_number = q.season_number
    AND p.mode = q.mode
    AND p.region = q.region
WHERE p.updated
ORDER BY
    p.season_number,
    p.mode,
    p.region,
    p.player_id,
    p.timestamp;
"""

RACE_TO_5000_HISTORICAL_QUERY = """
WITH current_season AS (
    SELECT MAX(season_number) AS season_number
    FROM xscraper.players
),
qualifying_runs AS (
    SELECT
        p.player_id,
        p.season_number,
        p.mode,
        p.region,
        MAX(p.x_power) AS peak_x_power
    FROM xscraper.players p
    JOIN current_season cs
        ON p.season_number < cs.season_number
    WHERE p.updated
    GROUP BY
        p.player_id,
        p.season_number,
        p.mode,
        p.region
    HAVING MAX(p.x_power) >= :threshold
)
SELECT
    p.player_id,
    p.splashtag,
    p.rank,
    p.x_power,
    p.timestamp,
    p.mode,
    p.region,
    p.season_number
FROM xscraper.players p
JOIN qualifying_runs q
    ON p.player_id = q.player_id
    AND p.season_number = q.season_number
    AND p.mode = q.mode
    AND p.region = q.region
WHERE p.updated
ORDER BY
    p.season_number,
    p.mode,
    p.region,
    p.player_id,
    p.timestamp;
"""
