from functools import cache

import requests

BASE_CDN_URL = "https://splat-top.nyc3.cdn.digitaloceanspaces.com/"
WEAPON_XREF_PATH = "assets/weapon_flat/WeaponInfoMain.json"
BADGE_XREF_PATH = "assets/badge/BadgeInfo.json"
BANNER_XREF_PATH = "assets/npl/NamePlateBgInfo.json"


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
    return f"{BASE_CDN_URL}assets/weapon_flat/{name}.png"


def get_badge_image(badge_id: int | str | None) -> str:
    if badge_id is None:
        return ""
    else:
        badge_id = int(badge_id)
    name = get_badge_name(badge_id)
    return f"{BASE_CDN_URL}assets/badge/{name}.png"


def get_banner_image(banner_id: int) -> str:
    name = get_banner_name(banner_id)
    return f"{BASE_CDN_URL}assets/npl/{name}.png"
