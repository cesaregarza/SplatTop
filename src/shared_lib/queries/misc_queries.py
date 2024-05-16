ALIAS_QUERY = "SELECT * FROM xscraper.aliases"

WEAPON_LEADERBOARD_QUERY = """
SELECT player_id, weapon_id, mode, region
FROM xscraper.players
WHERE season_number = :season_number AND updated = true
"""