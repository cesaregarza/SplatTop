WEAPON_LEADERBOARD_QUERY = """
SELECT *
FROM xscraper.weapon_leaderboard;
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
    AND updated
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
    xscraper.season_results;
"""

WEAPON_LEADERBOARD_SQLITE_QUERY = """
WITH latest_aliases AS (
    SELECT
        player_id,
        alias
    FROM
        aliases
    WHERE
        (player_id, last_seen) IN (
            SELECT
                player_id,
                MAX(last_seen) AS last_seen
            FROM
                aliases
            GROUP BY
                player_id
        )
)
SELECT
    w.*,
    a.alias
FROM
    weapon_leaderboard_peak w
LEFT JOIN
    latest_aliases a
ON
    w.player_id = a.player_id
WHERE
    w.mode = :mode
    AND (w.region = :region OR :region IS NULL)
    AND w.percent_games_played >= :min_threshold
    AND (
        w.weapon_id = :weapon_id
        OR w.weapon_id = :additional_weapon_id
    );
"""

SEASON_RESULTS_SQLITE_QUERY = """
WITH latest_aliases AS (
    SELECT
        player_id,
        alias
    FROM
        aliases
    WHERE
        (player_id, last_seen) IN (
            SELECT
                player_id,
                MAX(last_seen) AS last_seen
            FROM
                aliases
            GROUP BY
                player_id
        )
),
filtered_weapons AS (
    SELECT
        *
    FROM
        weapon_leaderboard_peak
    WHERE
        mode = :mode
        AND (region = :region OR :region IS NULL)
        AND percent_games_played >= :min_threshold
        AND (
            weapon_id = :weapon_id
            OR weapon_id = :additional_weapon_id
        )
)
SELECT
    s.player_id,
    a.alias,
    s.season_number,
    s.rank,
    s.x_power,
    w.max_x_power,
    w.percent_games_played,
    w.games_played,
    w.weapon_id
FROM
    season_results s
LEFT JOIN
    latest_aliases a
ON
    s.player_id = a.player_id
INNER JOIN
    filtered_weapons w
ON
    s.player_id = w.player_id
    AND s.weapon_id = w.weapon_id
    AND (s.season_number - 1) = w.season_number
WHERE
    s.mode = :mode
    AND (s.region = :region OR :region IS NULL);
"""
