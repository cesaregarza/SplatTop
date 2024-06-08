import logging

import numpy as np
import orjson
import pandas as pd

from celery_app.connections import redis_conn
from celery_app.tasks.analytics.utils import (
    append_weapon_data,
    find_missing_weapon_ids,
    pull_all_latest_data,
)
from shared_lib.constants import GINI_COEFF_REDIS_KEY, LORENZ_CURVE_REDIS_KEY

logger = logging.getLogger(__name__)


def compute_lorenz_curve(df: pd.DataFrame) -> pd.Series:
    df = df.copy()
    lorenz_raw = (
        df.groupby("weapon_id")["xp_scaled"]
        .sum()
        .sort_values(ascending=True)
        .rename("count")
    )
    return lorenz_raw.cumsum() / lorenz_raw.sum()


def append_missing_weapon_data(lorenz_curve: pd.Series) -> pd.Series:
    missing_weapon_ids = find_missing_weapon_ids(lorenz_curve.reset_index())
    missing_weapon_data = pd.Series(
        np.zeros(len(missing_weapon_ids)), index=missing_weapon_ids
    )
    return (
        pd.concat([missing_weapon_data, lorenz_curve])
        .reset_index()
        .rename(columns={"index": "weapon_id", 0: "count"})
        .set_index("weapon_id")["count"]
    )


def compute_gini_coefficient(lorenz_curve: pd.Series) -> float:
    n = lorenz_curve.shape[0]
    # Ensure lorenz curve is percentile cumsum
    lorenz_curve = lorenz_curve.cumsum() / lorenz_curve.sum()
    lorenz_curve = lorenz_curve.sort_values(ascending=True)
    lorenz_curve = lorenz_curve.reset_index(drop=True)
    # If the smallest value isn't zero, add a zero at the beginning
    if lorenz_curve.index[0] != 0:
        lorenz_curve = pd.concat(
            [pd.Series([0], index=[0]), lorenz_curve]
        ).reset_index(drop=True)
        n += 1

    equality_values = pd.Series(np.linspace(0, 1, n + 1)[1:])
    return (equality_values - lorenz_curve.values).sum() / equality_values.sum()


def compute_lorenz_and_gini() -> None:
    df = pull_all_latest_data()
    lorenz_curve = compute_lorenz_curve(df)
    lorenz_curve = append_missing_weapon_data(lorenz_curve)
    gini_coefficient = compute_gini_coefficient(lorenz_curve)
    lorenz_df = lorenz_curve.reset_index().pipe(append_weapon_data)
    lorenz_df["diff"] = lorenz_df["count"].diff().fillna(0)

    redis_conn.set(GINI_COEFF_REDIS_KEY, str(gini_coefficient))
    redis_conn.set(
        LORENZ_CURVE_REDIS_KEY,
        orjson.dumps(lorenz_df.to_dict(orient="records")),
    )
