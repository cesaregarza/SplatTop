import logging

import orjson
import pandas as pd
from sqlalchemy import text

from celery_app.tasks.analytics.utils import (
    append_weapon_data,
    pull_all_latest_data,
)

logger = logging.getLogger(__name__)


def compute_gini_coefficient(df: pd.DataFrame) -> float:
    df = df.copy()
    df["rank"] = df["xp_scaled"].rank(pct=True)
    # gini = 1 - 2 * df["rank"].mul(df["xp_scaled"]).sum()
    return (
        df["rank"]
        .mul(df["xp_scaled"])
        .sum()
        .mul(2)
        .rsub(1)
    )
    return gini
