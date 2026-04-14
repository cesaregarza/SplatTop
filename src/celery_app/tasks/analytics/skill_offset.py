import logging

import numpy as np
import orjson
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from celery_app.connections import redis_conn
from celery_app.tasks.analytics.utils import (
    append_weapon_data,
    pull_all_latest_data,
)
from shared_lib.analytics import load_probabilities
from shared_lib.constants import MODES, REGIONS, SKILL_OFFSET_REDIS_KEY

logger = logging.getLogger(__name__)

NUM_BINS = 150
ALL_SLICE_KEY = "all"


def align_sorted_xp_scaled_to_surface(
    sorted_xp_scaled: pd.Series, target_size: int
) -> pd.Series:
    values = sorted_xp_scaled.to_numpy(dtype=float, copy=False)
    current_size = values.shape[0]

    if current_size == 0:
        raise ValueError("Cannot align an empty skill offset slice.")

    if current_size == target_size:
        return pd.Series(values)

    if current_size == 1:
        return pd.Series(np.repeat(values[0], target_size))

    source_percentiles = (np.arange(current_size) + 0.5) / current_size
    target_percentiles = (np.arange(target_size) + 0.5) / target_size
    aligned_values = np.interp(target_percentiles, source_percentiles, values)
    return pd.Series(aligned_values)


def map_indices_to_data(df: pd.DataFrame) -> pd.DataFrame:
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
        weapon_name = row["weapon_name"].iloc[0]
        weapon_image = row["weapon_image"]["first"]
        median = row["xp_scaled"]["median"]
        count = row["xp_scaled"]["count"]

        subset = df_melted.query("k == @count")
        if subset.empty:
            log_probs = interpolator(
                (df_melted["bin_center"], [count] * df_melted.shape[0]),
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

        def find_appropriate_bin_logprob(value: float) -> pd.Series:
            mask = (subset["lower"] <= value) & (subset["upper"] >= value)
            return subset.loc[mask, "log_prob"].iloc[0]

        median_logprob = find_appropriate_bin_logprob(median)

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
    probability_surface = load_probabilities()
    sorted_xp_scaled = align_sorted_xp_scaled_to_surface(
        sorted_xp_scaled, probability_surface.shape[0]
    )

    prob_df = pd.DataFrame(probability_surface)
    prob_df.columns = [int(x) * 2 + 1 for x in range(prob_df.shape[1])]
    prob_df["y"] = sorted_xp_scaled.values
    prob_df["y_bin"] = pd.cut(prob_df["y"], bins=NUM_BINS)
    prob_df_binned = (
        prob_df.groupby("y_bin", observed=False).sum().drop(columns="y")
    )
    df_sums = prob_df_binned.sum(axis=0)
    prob_df_logbin: pd.DataFrame = (
        prob_df_binned.div(df_sums, axis=1)
        .add(1e-10)
        .pipe(np.log)
        .reset_index()
    )
    prob_df_logbin["lower"] = (
        prob_df_logbin["y_bin"].apply(lambda x: x.left).astype(float)
    )
    prob_df_logbin["upper"] = (
        prob_df_logbin["y_bin"].apply(lambda x: x.right).astype(float)
    )
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


def subcompute_skill_offset(input_df: pd.DataFrame, label: str) -> pd.Series:
    diff = input_df["mode_logprob"].sub(input_df[label + "_logprob"])
    return (
        input_df[label]
        .sub(input_df["mode_bin_center"])
        .gt(0)
        .map({True: 1, False: -1})
        .mul(diff)
    )


def build_skill_offset_slice(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    df = map_indices_to_data(df)
    df["skill_offset"] = subcompute_skill_offset(df, "median")
    return df.to_dict(orient="records")


def build_skill_offset_payload(df: pd.DataFrame) -> dict[str, dict[str, list]]:
    payload = {
        ALL_SLICE_KEY: {
            ALL_SLICE_KEY: build_skill_offset_slice(df),
        }
    }

    for region in REGIONS:
        payload[ALL_SLICE_KEY][region] = build_skill_offset_slice(
            df[df["region"] == region]
        )

    for mode in MODES:
        mode_df = df[df["mode"] == mode]
        payload[mode] = {
            ALL_SLICE_KEY: build_skill_offset_slice(mode_df),
        }
        for region in REGIONS:
            payload[mode][region] = build_skill_offset_slice(
                mode_df[mode_df["region"] == region]
            )

    return payload


def compute_skill_offset() -> None:
    df = pull_all_latest_data()
    df = append_weapon_data(df)
    payload = build_skill_offset_payload(df)

    redis_conn.set(SKILL_OFFSET_REDIS_KEY, orjson.dumps(payload))
