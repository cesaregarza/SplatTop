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
