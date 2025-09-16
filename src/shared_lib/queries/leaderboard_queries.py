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
    MAX(a.alias) AS alias,
    s.season_number,
    MAX(s.rank) AS rank,
    MAX(s.x_power) AS x_power,
    MAX(w.max_x_power) AS max_x_power,
    MAX(w.percent_games_played) AS percent_games_played,
    MAX(w.games_played) AS games_played,
    s.weapon_id
FROM
    season_results s
LEFT JOIN
    latest_aliases a ON s.player_id = a.player_id
INNER JOIN
    filtered_weapons w ON s.player_id = w.player_id
                       AND s.weapon_id = w.weapon_id
                       AND (s.season_number - 1) = w.season_number
WHERE
    s.mode = :mode
    AND (s.region = :region OR :region IS NULL)
GROUP BY
    s.player_id, s.season_number, s.weapon_id
ORDER BY
    x_power DESC;
"""

ALL_PEAKS_SQLITE_QUERY = """
WITH player_rankings AS (
    SELECT 
        player_id, 
        season_number, 
        mode, 
        region, 
        MAX(x_power) AS peak_x_power,
        ROW_NUMBER() OVER (
            PARTITION BY season_number, mode, region 
            ORDER BY MAX(x_power) DESC
        ) AS rank
    FROM
        xscraper.players
    WHERE
        updated
    GROUP BY
        player_id, season_number, mode, region
),
ranked_players AS (
    SELECT 
        pr.player_id,
        pr.season_number, 
        pr.mode, 
        pr.region, 
        pr.peak_x_power,
        pr.rank,
        p.splashtag
    FROM
        player_rankings pr
    JOIN xscraper.players p ON pr.player_id = p.player_id
        AND pr.season_number = p.season_number
        AND pr.mode = p.mode
        AND pr.region = p.region
        AND pr.peak_x_power = p.x_power
    WHERE
        p.updated
    GROUP BY
        pr.player_id, pr.season_number, pr.mode, pr.region, pr.peak_x_power, pr.rank, p.splashtag
)
SELECT 
    splashtag,
    season_number, 
    mode, 
    CASE WHEN region THEN 'Takoroka' ELSE 'Tentatek' END AS region, 
    peak_x_power
FROM
    ranked_players
WHERE
    rank <= 500
ORDER BY
    peak_x_power DESC;
"""
