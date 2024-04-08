import datetime as dt
from functools import cache

import requests

BASE_CDN_URL = "https://splat-top.nyc3.cdn.digitaloceanspaces.com/"
WEAPON_XREF_PATH = "assets/weapon_flat/WeaponInfoMain.json"
BADGE_XREF_PATH = "assets/badge/BadgeInfo.json"
BANNER_XREF_PATH = "assets/npl/NamePlateBgInfo.json"


def get_seasons(now_date: dt.datetime) -> list[tuple[dt.datetime, str]]:
    # Earliest season is 2022-09-01
    first_season = dt.datetime(2022, 9, 1)
    seasons_dict = {
        3: "Fresh",
        6: "Sizzle",
        9: "Drizzle",
        12: "Chill",
    }
    # Generate all seasons from 2022-09-01 to now
    return [
        (dt.datetime(year, month, 1), f"{seasons_dict[month]} Season {year}")
        for year in range(2022, now_date.year + 1)
        for month in seasons_dict.keys()
        if dt.datetime(year, month, 1) >= first_season
        and (
            year < now_date.year
            or (year == now_date.year and month <= now_date.month)
        )
    ]


def calculate_cache_refresh(
    reference_time: dt.datetime,
    target_time: dt.datetime,
    barriers: list[int],
    max_cache_time: int,
) -> bool:
    if (target_time - reference_time).total_seconds() < 0:
        return True
    if (target_time - reference_time).total_seconds() > max_cache_time:
        return True

    # Check if the target time has crossed a barrier
    reference_minute = reference_time.minute
    target_minute = target_time.minute
    wrapped = target_minute < reference_minute
    barriers = sorted(barriers)

    for barrier in barriers:
        if wrapped:
            # If wrapped, we only need to check if the first barrier is crossed
            return barrier <= target_minute

        if barrier <= reference_minute:
            continue
        if barrier <= target_minute:
            return True
    return False


@cache
def get_weapon_xref() -> dict:
    return requests.get(f"{BASE_CDN_URL}{WEAPON_XREF_PATH}").json()


@cache
def get_badge_xref() -> dict:
    return requests.get(f"{BASE_CDN_URL}{BADGE_XREF_PATH}").json()


@cache
def get_banner_xref() -> dict:
    return requests.get(f"{BASE_CDN_URL}{BANNER_XREF_PATH}").json()


def get_weapon_name(weapon_id: int) -> str:
    weapon_xref = get_weapon_xref()
    for weapon in weapon_xref:
        if weapon["Id"] == weapon_id:
            return weapon["__RowId"]


def get_badge_name(badge_id: int) -> str:
    badge_xref = get_badge_xref()
    for badge in badge_xref:
        if badge["Id"] == badge_id:
            return badge["Name"]


def get_banner_name(banner_id: int) -> str:
    banner_xref = get_banner_xref()
    for banner in banner_xref:
        if banner["Id"] == banner_id:
            return banner["__RowId"]


def get_weapon_image(weapon_id: int) -> str:
    name = get_weapon_name(weapon_id)
    return f"{BASE_CDN_URL}assets/weapon_flat/Path_Wst_{name}.png"


def get_badge_image(badge_id: int | str | None) -> str:
    if badge_id is None:
        return ""
    else:
        badge_id = int(badge_id)
    name = get_badge_name(badge_id)
    return f"{BASE_CDN_URL}assets/badge/Badge_{name}.png"


def get_banner_image(banner_id: int) -> str:
    name = get_banner_name(banner_id)
    return f"{BASE_CDN_URL}assets/npl/Npl_{name}.png"
