import logging

import orjson

from fast_api_app.connections import redis_conn, sqlite_conn, sqlite_cursor
from fast_api_app.sqlite_tables.main import TableManager

logger = logging.getLogger(__name__)


class WeaponLeaderboardManager(TableManager):
    def initialize_table(self) -> None:
        sqlite_cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
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
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_player_id 
            ON {self.table_name} (player_id);
            """
        )
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_season_number 
            ON {self.table_name} (season_number);
            """
        )
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_mode 
            ON {self.table_name} (mode);
            """
        )
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_region 
            ON {self.table_name} (region);
            """
        )
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_weapon_id 
            ON {self.table_name} (weapon_id);
            """
        )
        sqlite_conn.commit()

    def insert_data(self, data: dict) -> None:
        sqlite_cursor.execute(
            f"""
            INSERT INTO {self.table_name} (
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
            (
                data["player_id"],
                data["season_number"],
                data["mode"],
                data["region"],
                data["weapon_id"],
                data["max_x_power"],
                data["games_played"],
                data["percent_games_played"],
            ),
        )
        sqlite_conn.commit()

    def update_database(self) -> None:
        logger.info("Updating SQLite table %s", self.table_name)
        weapon_leaderboard_peak_data = redis_conn.get(self.redis_key)
        if weapon_leaderboard_peak_data:
            weapon_leaderboard_peak = orjson.loads(weapon_leaderboard_peak_data)
            sqlite_cursor.execute(f"DELETE FROM {self.table_name};")
            for player_dict in weapon_leaderboard_peak:
                self.insert_data(player_dict)
            sqlite_conn.commit()
            logger.info(
                "SQLite database updated with new weapon leaderboard peak data "
                "with %d rows",
                len(weapon_leaderboard_peak),
            )
        else:
            logger.warning("Weapon leaderboard peak data not found in Redis")
            raise Exception("Weapon leaderboard peak data not found in Redis")


class SeasonResultsManager(TableManager):
    def initialize_table(self) -> None:
        sqlite_cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
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
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_player_id 
            ON {self.table_name} (player_id);
            """
        )
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_season_number 
            ON {self.table_name} (season_number);
            """
        )
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_mode 
            ON {self.table_name} (mode);
            """
        )
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_region 
            ON {self.table_name} (region);
            """
        )
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_weapon_id 
            ON {self.table_name} (weapon_id);
            """
        )
        sqlite_conn.commit()

    def insert_data(self, data: dict) -> None:
        sqlite_cursor.execute(
            f"""
            INSERT INTO {self.table_name} (
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
            (
                data["player_id"],
                data["season_number"],
                data["mode"],
                data["region"],
                data["weapon_id"],
                data["x_power"],
                data["rank"],
            ),
        )

    def update_database(self) -> None:
        logger.info("Updating SQLite table %s", self.table_name)
        season_results_data = redis_conn.get(self.redis_key)
        if season_results_data:
            season_results = orjson.loads(season_results_data)
            sqlite_cursor.execute(f"DELETE FROM {self.table_name};")
            for player_dict in season_results:
                self.insert_data(player_dict)
            sqlite_conn.commit()
            logger.info(
                "SQLite database updated with new season results data with "
                "%d rows",
                len(season_results),
            )
        else:
            logger.warning("Season results data not found in Redis")
            raise Exception("Season results data not found in Redis")
