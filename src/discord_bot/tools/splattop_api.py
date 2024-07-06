from datetime import timedelta

import cachetools
import orjson
import requests

TRANSLATION_URL = "https://splat.top/api/game_translation"
WEAPON_INFO_URL = "https://splat.top/api/weapon_info"

translation_cache = cachetools.TTLCache(
    maxsize=1, ttl=timedelta(hours=1).total_seconds()
)
weapon_info_cache = cachetools.TTLCache(
    maxsize=1, ttl=timedelta(hours=1).total_seconds()
)
translation_id_xref_cache = cachetools.TTLCache(
    maxsize=1, ttl=timedelta(hours=1).total_seconds()
)


@cachetools.cached(cache=translation_cache)
def get_translation() -> dict:
    response = requests.get(TRANSLATION_URL)
    response.raise_for_status()
    return orjson.loads(response.content)


@cachetools.cached(cache=weapon_info_cache)
def get_weapon_info() -> dict:
    response = requests.get(WEAPON_INFO_URL)
    response.raise_for_status()
    return orjson.loads(response.content)


def reset_all_caches():
    translation_cache.clear()
    weapon_info_cache.clear()
    translation_id_xref_cache.clear()


@cachetools.cached(cache=translation_id_xref_cache)
def translation_id_xref() -> dict[str, dict[str, str]]:
    translation_data = get_translation()
    weapon_info_data = get_weapon_info()

    weapon_id_reference = {}
    for weapon_id, weapon_data in weapon_info_data.items():
        weapon_class = weapon_data["class"]
        weapon_kit = weapon_data["kit"]
        weapon_reference = f"{weapon_class}_{weapon_kit}"
        weapon_id_reference[weapon_reference] = weapon_id

    weapon_id_xref: dict[str, dict[str, str]] = {}
    for language_key, language_data in translation_data.items():
        main_weapon_data: dict[str, str] = language_data["WeaponName_Main"]
        weapon_id_xref[language_key] = {}
        for weapon_ref, weapon_name in main_weapon_data.items():
            try:
                weapon_id_xref[language_key][weapon_name] = weapon_id_reference[
                    weapon_ref
                ]
            except KeyError:
                pass

    return weapon_id_xref


def translation_languages() -> list[str]:
    translation_data = get_translation()
    return list(translation_data.keys())


def weapon_id_xref(language: str) -> dict[str, str]:
    return translation_id_xref()[language]


WEAPON_XREF_DEFINITION = {
    "function": weapon_id_xref,
    "name": "weapon_info",
    "description": "Gets the weapon info data from splat.top",
    "input_schema": {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "enum": translation_languages(),
                "description": (
                    "The language code to use for the weapon name translations "
                    "on splat.top. These language codes consist of two "
                    "two-letter codes concatenated together, "
                    "[region code][language code] (e.g. USen, JPja)"
                ),
            }
        },
        "required": ["language"],
    },
}
