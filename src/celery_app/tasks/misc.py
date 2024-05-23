import logging

import orjson
import requests
from sqlalchemy import text

from celery_app.connections import Session, redis_conn
from shared_lib.constants import (
    ALIASES_REDIS_KEY,
    GAME_TRANSLATION_BASE_URL,
    GAME_TRANSLATION_REDIS_KEY,
    LANGUAGES,
    WEAPON_INFO_REDIS_KEY,
    WEAPON_INFO_URL,
)
from shared_lib.queries.misc_queries import ALIAS_QUERY

logger = logging.getLogger(__name__)


def update_weapon_info() -> None:
    logging.info("Running task: update_weapon_info")
    response = requests.get(WEAPON_INFO_URL)
    weapon_info = orjson.loads(response.text)
    language_data = {}
    for language in LANGUAGES:
        response = requests.get(GAME_TRANSLATION_BASE_URL % language)
        language_data[language] = orjson.loads(response.text)

    redis_conn.set(WEAPON_INFO_REDIS_KEY, orjson.dumps(weapon_info))
    logging.info("Weapon info updated in Redis.")
    redis_conn.set(GAME_TRANSLATION_REDIS_KEY, orjson.dumps(language_data))
    logging.info("Weapon translations updated in Redis.")


def pull_aliases() -> None:
    logging.info("Running task: fetch_aliases")
    query = text(ALIAS_QUERY)
    with Session() as session:
        result = session.execute(query).fetchall()

    aliases = [{**row._asdict()} for row in result]
    redis_conn.set(ALIASES_REDIS_KEY, orjson.dumps(aliases))
    logging.info("Aliases updated in Redis.")
