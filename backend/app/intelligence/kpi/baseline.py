from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.common.date_parse import parse_dates_robust
from app.intelligence.kpi.compilers import PandasCompiler
from app.intelligence.kpi.ir import Expr


# A month counts as complete once the data reaches this share of its days (Dec 30 of 31 counts).
_COMPLETE_SHARE = 0.9


@dataclass(frozen=True)
class Baseline:
    text: str
    current: float
    previous: float
    change_pct: Optional[float]


def _format(value: float) -> str:
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:,.2f}"


def period_baseline(expr: Expr, df: pd.DataFrame, date_column: str) -> Optional[Baseline]:
    """
    The KPI's latest calendar month against the month before it, computed on the data.

    This is the only benchmark PowerPilot can state without inventing one. It needs a date
    column spanning at least two months; otherwise there is nothing honest to compare to.
    """
    dates = parse_dates_robust(df[date_column])
    valid = dates.notna()
    if not valid.any():
        return None

    months = dates.dt.to_period("M")
    distinct = sorted(months[valid].unique())
    last_day = dates[valid].max()

    label, caveat = "Latest month", ""
    if last_day.day / distinct[-1].days_in_month < _COMPLETE_SHARE:
        # Comparing a few days of data with a whole month would show a fake collapse.
        partial = distinct.pop()
        label = "Latest complete month"
        caveat = f"; {partial} left out because its data ends {last_day:%Y-%m-%d}"
    if len(distinct) < 2:
        return None
    latest, earlier = distinct[-1], distinct[-2]

    evaluator = PandasCompiler()
    current = evaluator.evaluate(expr, df[months == latest])
    previous = evaluator.evaluate(expr, df[months == earlier])
    if current is None or previous is None:
        return None

    change = (current - previous) / abs(previous) * 100 if previous != 0 else None
    text = f"{label} {latest} vs {earlier}: {_format(current)} vs {_format(previous)}"
    if change is not None:
        text += f" ({change:+.1f}%)"
    return Baseline(text=text + caveat, current=current, previous=previous, change_pct=change)
