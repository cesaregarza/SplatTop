WEAPON_LEADERBOARD_QUERY = """
SELECT *
FROM xscraper.weapon_leaderboard
"""

LIVE_WEAPON_LEADERBOARD_QUERY = """
SELECT 
    player_id,
    season_number,
    mode,
    region,
    weapon_id,
    MAX(x_power) AS max_x_power,
    COUNT(*) AS games_played
FROM
    xscraper.players
WHERE
    season_number = (SELECT MAX(season_number) FROM xscraper.players)
    AND
    updated
GROUP BY
    player_id,
    season_number,
    mode,
    region,
    weapon_id
ORDER BY
    player_id,
    season_number,
    mode,
    region,
    weapon_id;
"""

SEASON_RESULTS_QUERY = """
SELECT 
    *
FROM
    xscraper.season_results
"""
