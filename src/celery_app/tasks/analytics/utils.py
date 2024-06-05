import logging

import orjson
import pandas as pd
import requests
from sqlalchemy import text

from celery_app.connections import Session
from shared_lib.constants import BASE_CDN_URL, MODES, REGIONS, WEAPON_INFO_URL
from shared_lib.queries.analytics_queries import ANALYTICS_QUERY

logger = logging.getLogger(__name__)


def fetch_leaderboard_data(mode: str, region_bool: bool) -> pd.DataFrame:
    with Session() as session:
        return pd.read_sql(
            text(ANALYTICS_QUERY),
            session.connection(),
            params={"mode": mode, "region": region_bool},
        )


def pull_all_latest_data() -> pd.DataFrame:
    out = []
    for mode in MODES:
        for region in REGIONS:
            player_df = fetch_leaderboard_data(mode, region == "Takoroka")
            xp_min = player_df["x_power"].min()
            xp_max = player_df["x_power"].max()
            player_df["xp_scaled"] = (
                player_df["x_power"].sub(xp_min).div(xp_max - xp_min)
            )
            out.append(player_df)
    return pd.concat(out)


def append_weapon_data(df: pd.DataFrame) -> pd.DataFrame:
    response = requests.get(WEAPON_INFO_URL)
    weapon_info = orjson.loads(response.text)
    weapon_dict_series = df["weapon_id"].astype(str).map(weapon_info)
    df["weapon_name"] = (
        weapon_dict_series.str["class"]
        .add("_")
        .add(weapon_dict_series.str["reference_kit"])
    )
    df["weapon_image"] = (
        df["weapon_name"]
        .radd(f"{BASE_CDN_URL}assets/weapon_flat/Path_Wst_")
        .add(".png")
    )
    return df


def find_missing_weapon_ids(df: pd.DataFrame) -> list:
    response = requests.get(WEAPON_INFO_URL)
    weapon_info: dict = orjson.loads(response.text)
    unique_weapon_ids = set()
    for _, value in weapon_info.items():
        unique_weapon_ids.add(value["reference_id"])

    ref_ids = df["weapon_id"].astype(str).map(weapon_info).str["reference_id"]
    return list(unique_weapon_ids - set(ref_ids))
