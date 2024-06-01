ANALYTICS_QUERY = """
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
LatestWeaponData AS (
    SELECT 
        pl.player_id, 
        pl.mode, 
        p.weapon_id
    FROM xscraper.player_latest pl
    JOIN xscraper.players p 
    ON pl.player_id = p.player_id 
    AND pl.mode = p.mode
    WHERE p.timestamp = (
        SELECT MAX(p2.timestamp)
        FROM xscraper.players p2
        WHERE p2.player_id = pl.player_id
        AND p2.mode = pl.mode
    )
    AND pl.mode = :mode
)
SELECT 
    f.player_id,
    f.x_power,
    lw.weapon_id
FROM FilteredByTimestamp f
LEFT JOIN LatestWeaponData lw
    ON f.player_id = lw.player_id
WHERE f.mode = :mode
    AND f.region = :region
ORDER BY f.rank ASC;
"""
