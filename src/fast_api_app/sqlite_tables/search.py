import logging

import orjson

from fast_api_app.connections import redis_conn, sqlite_conn, sqlite_cursor
from fast_api_app.sqlite_tables.main import TableManager
from shared_lib.constants import AUTOMATON_IS_VALID_REDIS_KEY

logger = logging.getLogger(__name__)


class AliasManager(TableManager):
    def initialize_table(self) -> None:
        sqlite_cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                alias TEXT,
                player_id TEXT,
                last_seen DATETIME
            );
            """
        )
        sqlite_cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_alias 
            ON {self.table_name} (alias);
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
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_last_seen 
            ON {self.table_name} (last_seen);
            """
        )
        sqlite_conn.commit()

    def insert_data(self, data: dict) -> None:
        sqlite_cursor.execute(
            f"""
            INSERT INTO {self.table_name} (alias, player_id, last_seen)
            VALUES (?, ?, ?);
            """,
            (data["alias"], data["player_id"], data["last_seen"]),
        )
        sqlite_conn.commit()

    def update_database(self) -> None:
        aliases_data = redis_conn.get(self.redis_key)
        if aliases_data:
            aliases = orjson.loads(aliases_data)
            sqlite_cursor.execute(f"DELETE FROM {self.table_name};")
            for player_dict in aliases:
                self.insert_data(
                    {
                        "alias": player_dict["splashtag"],
                        "player_id": player_dict["player_id"],
                        "last_seen": player_dict["last_seen"],
                    }
                )

            sqlite_conn.commit()
            logger.info("SQLite database updated for %s", self.table_name)
            redis_conn.set(AUTOMATON_IS_VALID_REDIS_KEY, 1, ex=3600)
        else:
            logger.warning("Data not found in Redis for key %s", self.redis_key)
            raise Exception(f"Data not found in Redis for key {self.redis_key}")
