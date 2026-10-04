"""False-insight rate: how many relationship claims does the pipeline make on data where none can exist?

Each column of the dataset is shuffled independently (fixed seed). Marginal distributions are untouched, but every
relationship between columns and every trend over time is destroyed. So any CORRELATION or TREND insight on the shuffled
copy is false by construction. ANOMALY, KPI and BUSINESS_RULE insights are about single columns and may legitimately
survive shuffling, so they are not counted.
"""

from __future__ import annotations

import zlib
from typing import Any

import numpy as np
import pandas as pd

CLAIM_CATEGORIES = ("CORRELATION", "TREND")


def shuffle_columns(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    out = frame.copy()
    for i, column in enumerate(out.columns):
        rng = np.random.default_rng([seed, zlib.crc32(str(column).encode()), i])
        out[column] = rng.permutation(out[column].to_numpy())
    return out


def claim_count(result: Any) -> dict:
    insights = result.insight_report.insights
    by = {c: sum(1 for i in insights if i.category == c) for c in CLAIM_CATEGORIES}
    return {"claims": sum(by.values()), **{c.lower(): n for c, n in by.items()}, "insights": len(insights)}
