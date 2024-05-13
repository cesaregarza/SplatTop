import logging

import orjson

from fast_api_app.connections import redis_conn, sqlite_conn, sqlite_cursor
from shared_lib.constants import ALIASES_REDIS_KEY, AUTOMATON_IS_VALID_REDIS_KEY

logger = logging.getLogger(__name__)


def initialize_database() -> None:
    sqlite_cursor.execute(
        "CREATE TABLE IF NOT EXISTS player_data (key TEXT, value TEXT);"
    )
    sqlite_conn.commit()


def insert_data(key: str, value: str) -> None:
    sqlite_cursor.execute(
        "INSERT INTO player_data (key, value) VALUES (?, ?);",
        (key, value),
    )
    sqlite_conn.commit()


def search_data(key: str) -> list:
    formatted_key = f"%{key}%"
    logger.info(f"Searching for: {formatted_key}")
    sqlite_cursor.execute(
        "SELECT key, value FROM player_data WHERE key LIKE ?",
        (formatted_key,),
    )
    logger.info(f"Search complete for: {formatted_key}")
    return sqlite_cursor.fetchall()


def update_database() -> None:
    aliases_data = redis_conn.get(ALIASES_REDIS_KEY)
    if aliases_data:
        aliases = orjson.loads(aliases_data)
        # Clear existing data
        sqlite_cursor.execute("DELETE FROM player_data;")
        for player_dict in aliases:
            alias = player_dict["splashtag"]
            player_id = player_dict["player_id"]
            insert_data(alias, player_id)

        sqlite_conn.commit()
        logger.info("SQLite database updated with new aliases")

        redis_conn.set(AUTOMATON_IS_VALID_REDIS_KEY, 1, ex=3600)
    else:
        logger.warning("Aliases data not found in Redis")
        raise Exception("Aliases data not found in Redis")


initialize_database()
