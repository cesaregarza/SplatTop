import logging

import numpy as np
import orjson
import pandas as pd
from sqlalchemy import text

from celery_app.connections import redis_conn
from celery_app.tasks.analytics.utils import (
    append_weapon_data,
    pull_all_latest_data,
)

logger = logging.getLogger(__name__)


def setup_gini_coefficient(df: pd.DataFrame) -> float:
    df = df.copy()
    n = df.shape[0]
    lorenz_raw = (
        df.groupby("weapon_id")
        .size()
        .sort_values(ascending=True)
        .rename("count")
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

    equality_values = pd.Series(np.linspace(0, 1, n)[1:])
    return (equality_values - lorenz_curve.values).sum() / equality_values.sum()
