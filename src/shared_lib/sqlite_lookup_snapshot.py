from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Mapping


LOOKUP_SNAPSHOT_SCHEMA_VERSION = 1


def create_lookup_snapshot_database(
    db_path: str | Path,
) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=OFF;")
    connection.execute("PRAGMA synchronous=OFF;")
    connection.execute("PRAGMA temp_store=MEMORY;")
    connection.execute("PRAGMA foreign_keys=OFF;")
    _initialize_lookup_tables(connection)
    return connection


def _initialize_lookup_tables(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS aliases (
            alias TEXT,
            player_id TEXT,
            last_seen DATETIME
        );
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_aliases_alias
        ON aliases (alias);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_aliases_player_id
        ON aliases (player_id);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_aliases_last_seen
        ON aliases (last_seen);
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS weapon_leaderboard_peak (
            player_id TEXT,
            season_number INTEGER,
            mode TEXT,
            region BOOLEAN,
            weapon_id INTEGER,
            max_x_power REAL,
            games_played INTEGER,
            percent_games_played REAL,
            PRIMARY KEY (player_id, season_number, mode, region, weapon_id)
        );
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_weapon_leaderboard_peak_player_id
        ON weapon_leaderboard_peak (player_id);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_weapon_leaderboard_peak_season_number
        ON weapon_leaderboard_peak (season_number);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_weapon_leaderboard_peak_mode
        ON weapon_leaderboard_peak (mode);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_weapon_leaderboard_peak_region
        ON weapon_leaderboard_peak (region);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_weapon_leaderboard_peak_weapon_id
        ON weapon_leaderboard_peak (weapon_id);
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS season_results (
            player_id TEXT,
            season_number INTEGER,
            mode TEXT,
            region BOOLEAN,
            weapon_id INTEGER,
            x_power REAL,
            rank INTEGER,
            PRIMARY KEY (player_id, season_number, mode, region)
        );
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_season_results_player_id
        ON season_results (player_id);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_season_results_season_number
        ON season_results (season_number);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_season_results_mode
        ON season_results (mode);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_season_results_region
        ON season_results (region);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_season_results_weapon_id
        ON season_results (weapon_id);
        """
    )
    connection.commit()


def populate_lookup_snapshot_database(
    connection: sqlite3.Connection,
    *,
    aliases: Iterable[Mapping[str, object]],
    weapon_rows: Iterable[Mapping[str, object]],
    season_rows: Iterable[Mapping[str, object]],
) -> dict[str, int]:
    alias_rows = [
        (
            row.get("splashtag"),
            row.get("player_id"),
            row.get("last_seen"),
        )
        for row in aliases
    ]
    weapon_values = [
        (
            row.get("player_id"),
            row.get("season_number"),
            row.get("mode"),
            row.get("region"),
            row.get("weapon_id"),
            row.get("max_x_power"),
            row.get("games_played"),
            row.get("percent_games_played"),
        )
        for row in weapon_rows
    ]
    season_values = [
        (
            row.get("player_id"),
            row.get("season_number"),
            row.get("mode"),
            row.get("region"),
            row.get("weapon_id"),
            row.get("x_power"),
            row.get("rank"),
        )
        for row in season_rows
    ]

    with connection:
        connection.execute("DELETE FROM aliases;")
        connection.executemany(
            """
            INSERT INTO aliases (alias, player_id, last_seen)
            VALUES (?, ?, ?);
            """,
            alias_rows,
        )
        connection.execute("DELETE FROM weapon_leaderboard_peak;")
        connection.executemany(
            """
            INSERT INTO weapon_leaderboard_peak (
                player_id,
                season_number,
                mode,
                region,
                weapon_id,
                max_x_power,
                games_played,
                percent_games_played
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            weapon_values,
        )
        connection.execute("DELETE FROM season_results;")
        connection.executemany(
            """
            INSERT INTO season_results (
                player_id,
                season_number,
                mode,
                region,
                weapon_id,
                x_power,
                rank
            )
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            season_values,
        )

    return {
        "aliases": len(alias_rows),
        "weapon_leaderboard_peak": len(weapon_values),
        "season_results": len(season_values),
    }


def create_empty_lookup_snapshot(db_path: str | Path) -> None:
    connection = create_lookup_snapshot_database(db_path)
    try:
        populate_lookup_snapshot_database(
            connection,
            aliases=[],
            weapon_rows=[],
            season_rows=[],
        )
    finally:
        connection.close()
