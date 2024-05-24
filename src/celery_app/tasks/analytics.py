import logging

import numpy as np
import orjson
import pandas as pd
import requests
from scipy.interpolate import RegularGridInterpolator

from celery_app.connections import redis_conn
from shared_lib.analytics import load_probabilities
from shared_lib.constants import (
    BASE_CDN_URL,
    MODES,
    REGIONS,
    SKILL_OFFSET_REDIS_KEY,
    WEAPON_INFO_URL,
)

logger = logging.getLogger(__name__)

NUM_BINS = 150


def pull_all_latest_data() -> pd.DataFrame:
    out = []
    for mode in MODES:
        for region in REGIONS:
            redis_key = f"leaderboard_data:{mode}:{region}"
            players = redis_conn.get(redis_key)
            player_df = pd.DataFrame(orjson.loads(players))
            player_df["mode"] = mode
            player_df["region"] = region
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


def map_data_to_indices(df: pd.DataFrame) -> pd.DataFrame:
    agg_data = (
        df.groupby("weapon_name")
        .agg(
            {
                "xp_scaled": ["median", "count"],
                "weapon_image": "first",
            }
        )
        .reset_index()
    )
    df_melted = compute_probability_map(df["xp_scaled"].sort_values())
    interpolator = create_interpolator(df_melted)

    results = []
    for _, row in agg_data.iterrows():
        weapon_name = row["weapon_name"]
        weapon_image = row["weapon_image"]
        median = row["xp_scaled"]["median"]
        count = row["xp_scaled"]["count"]

        subset = df_melted.query("k == @count")
        if subset.empty:
            log_probs = interpolator(
                df_melted["bin_center"],
                [count] * df_melted.shape[0],
            )
            subset = pd.DataFrame(
                {
                    "bin_center": df_melted["bin_center"],
                    "log_prob": log_probs,
                    "lower": df_melted["lower"],
                    "upper": df_melted["upper"],
                }
            )

        # Find the mode and its log probability
        mode_row = subset.loc[subset["log_prob"].idxmax()]
        mode_logprob = mode_row["log_prob"]
        mode_bin_center = mode_row["bin_center"]

        # Find the median log probability
        median_bin_row = subset.query(
            "(lower <= @median) & (upper >= @median)"
        ).iloc[0]
        median_logprob = median_bin_row["log_prob"]
        results.append(
            {
                "weapon_name": weapon_name,
                "weapon_image": weapon_image,
                "count": count,
                "median": median,
                "mode_logprob": mode_logprob,
                "mode_bin_center": mode_bin_center,
                "median_logprob": median_logprob,
            }
        )

    return pd.DataFrame(results)


def compute_probability_map(sorted_xp_scaled: pd.Series) -> pd.DataFrame:
    prob_df = pd.DataFrame(load_probabilities())
    prob_df.columns = [int(x) * 2 + 1 for x in range(prob_df.shape[1])]
    prob_df["y"] = sorted_xp_scaled.values
    prob_df["y_bin"] = pd.cut(prob_df["y"], bins=NUM_BINS)
    prob_df_binned = prob_df.groupby("y_bin").sum().drop(columns="y")
    df_sums = prob_df_binned.sum(axis=0)
    prob_df_logbin: pd.DataFrame = (
        prob_df_binned.div(df_sums, axis=1)
        .add(1e-10)
        .pipe(np.log)
        .reset_index()
    )
    prob_df_logbin["lower"] = prob_df_logbin["y_bin"].apply(lambda x: x.left)
    prob_df_logbin["upper"] = prob_df_logbin["y_bin"].apply(lambda x: x.right)
    prob_df_logbin = prob_df_logbin.drop(columns="y_bin")
    prob_df_logbin["bin_center"] = (
        prob_df_logbin["lower"].add(prob_df_logbin["upper"]).div(2)
    )

    df_melted = prob_df_logbin.melt(
        id_vars=["bin_center", "lower", "upper"],
        var_name="k",
        value_name="log_prob",
    )
    df_melted["k"] = df_melted["k"].astype(int)
    return df_melted


def create_interpolator(df_melted: pd.DataFrame) -> RegularGridInterpolator:
    k_values = df_melted["k"].unique()
    y_values = df_melted["bin_center"].unique()
    data = df_melted.pivot(
        index="bin_center",
        columns="k",
        values="log_prob",
    ).values
    return RegularGridInterpolator((y_values, k_values), data, method="linear")


def compute_weapon_data() -> pd.DataFrame:
    df = pull_all_latest_data()
    df = append_weapon_data(df)
    df = map_data_to_indices(df)
    diff = df["mode_logprob"].sub(df["median_logprob"])
    df["directional_diff"] = (
        df["median"]
        .sub(df["mode_bin_center"])
        .gt(0)
        .replace({True: 1, False: -1})
        .mul(diff)
    )
    redis_conn.set(
        SKILL_OFFSET_REDIS_KEY, orjson.dumps(df.to_dict(orient="records"))
    )
