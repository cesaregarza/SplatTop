import logging

import orjson
import requests
from requests import RequestException
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

REQUEST_TIMEOUT_SECONDS = 10


def _fetch_json(url: str) -> object:
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return orjson.loads(response.content)


def update_weapon_info() -> None:
    logger.info("Running task: update_weapon_info")
    try:
        weapon_info = _fetch_json(WEAPON_INFO_URL)
    except (RequestException, orjson.JSONDecodeError) as exc:
        logger.error(
            "Failed to fetch weapon info from %s: %s",
            WEAPON_INFO_URL,
            exc,
        )
        return

    redis_conn.set(WEAPON_INFO_REDIS_KEY, orjson.dumps(weapon_info))
    logger.info("Weapon info updated in Redis.")

    language_data: dict[str, object] = {}
    for language in LANGUAGES:
        try:
            language_data[language] = _fetch_json(
                GAME_TRANSLATION_BASE_URL % language
            )
        except (RequestException, orjson.JSONDecodeError) as exc:
            logger.warning(
                "Skipping weapon translation for %s: %s",
                language,
                exc,
            )

    if not language_data:
        logger.warning(
            "No weapon translations fetched; leaving %s unchanged.",
            GAME_TRANSLATION_REDIS_KEY,
        )
        return

    merged_translations = language_data
    existing_translations_raw = redis_conn.get(GAME_TRANSLATION_REDIS_KEY)
    if existing_translations_raw:
        try:
            existing_translations = orjson.loads(existing_translations_raw)
        except orjson.JSONDecodeError:
            existing_translations = None

        if isinstance(existing_translations, dict):
            existing_translations.update(language_data)
            merged_translations = existing_translations

    redis_conn.set(GAME_TRANSLATION_REDIS_KEY, orjson.dumps(merged_translations))
    logger.info(
        "Weapon translations updated in Redis (%s/%s languages).",
        len(language_data),
        len(LANGUAGES),
    )


def pull_aliases() -> None:
    logger.info("Running task: fetch_aliases")
    query = text(ALIAS_QUERY)
    with Session() as session:
        result = session.execute(query).fetchall()

    aliases = [{**row._asdict()} for row in result]
    redis_conn.set(ALIASES_REDIS_KEY, orjson.dumps(aliases))
    logger.info("Aliases updated in Redis.")
