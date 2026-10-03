from __future__ import annotations

import math
from typing import Optional, Protocol

import pandas as pd

REL_TOL = 1e-6


class DaxExecutor(Protocol):
    """Runs a DAX measure body against the dataset in a real engine and returns its value.

    A local Analysis Services instance or the Power BI Modeling MCP can implement this.
    PowerPilot ships no concrete executor; the hook exists so one can be plugged in and
    the pandas value cross-checked against it (``POWERPILOT_DAX_ENGINE_CHECK``).
    """

    def execute(self, dax: str, table: str, df: pd.DataFrame) -> Optional[float]: ...


def disagreement(pandas_value: float, dax: str, table: str, df: pd.DataFrame, executor: DaxExecutor) -> Optional[str]:
    """None when the engine agrees with pandas to ``REL_TOL``; otherwise why the KPI is rejected."""
    try:
        engine_value = executor.execute(dax, table, df)
    except Exception as exc:
        return f"the DAX engine could not evaluate it: {exc}"
    if engine_value is None:
        return "the DAX engine returned BLANK where pandas computed a value"
    if not math.isclose(pandas_value, engine_value, rel_tol=REL_TOL, abs_tol=1e-9):
        return f"the DAX engine returned {engine_value:,.6g} but pandas computed {pandas_value:,.6g}"
    return None
