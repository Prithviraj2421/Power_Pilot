from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.common.powerbi_names import dax_references
from app.intelligence.kpi.compilers import DaxCompiler, PandasCompiler
from app.intelligence.kpi.ir import Compare, Difference, Expr, Measure, Op, Ratio, columns_of

_NUMERIC_OPS = {Op.SUM, Op.AVERAGE, Op.MIN, Op.MAX}
_ORDERED = {Compare.GT, Compare.GE, Compare.LT, Compare.LE}
# Share of a column's values that must be numbers before it may be summed or averaged. The
# rest are treated as blank, exactly as the exported Power Query script treats them.
MIN_NUMERIC_SHARE = 0.9
_COUNTROWS_TABLE = re.compile(r"COUNTROWS\('((?:[^']|'')+)'\)")


@dataclass(frozen=True)
class Verification:
    verified: bool
    note: str
    value: Optional[float] = None
    dax: Optional[str] = None


def _measures(expr: Expr) -> list[Measure]:
    if isinstance(expr, Measure):
        return [expr]
    if isinstance(expr, Ratio):
        return _measures(expr.numerator) + _measures(expr.denominator)
    return _measures(expr.minuend) + _measures(expr.subtrahend)


def _numeric_problem(df: pd.DataFrame, column: str, what: str) -> Optional[str]:
    series = df[column]
    if pd.api.types.is_bool_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
        return f"column '{column}' is {series.dtype}, which cannot be {what}"
    present = int(series.notna().sum())
    if present == 0:
        return f"column '{column}' has no values"
    share = pd.to_numeric(series, errors="coerce").notna().sum() / present
    if share < MIN_NUMERIC_SHARE:
        return f"only {share:.0%} of '{column}' values are numbers, so it cannot be {what}"
    return None


def _first_dtype_problem(expr: Expr, df: pd.DataFrame) -> Optional[str]:
    for measure in _measures(expr):
        if measure.op in _NUMERIC_OPS:
            problem = _numeric_problem(df, measure.column, "aggregated numerically")
            if problem:
                return problem
        flt = measure.filter
        if flt and flt.compare in _ORDERED:
            problem = _numeric_problem(df, flt.column, "compared with < or >")
            if problem:
                return problem
        if flt and flt.compare in _ORDERED | {Compare.NE} and df[flt.column].isna().any():
            # DAX gives BLANK its own comparison rules here, so pandas cannot vouch for the result.
            return f"filter column '{flt.column}' has blank values, which {flt.compare.value} treats differently in DAX"
    return None


def _blank_cells(expr: Expr, df: pd.DataFrame) -> list[str]:
    notes = []
    for measure in _measures(expr):
        if measure.op in _NUMERIC_OPS:
            series = df[measure.column]
            dropped = int(series.notna().sum() - pd.to_numeric(series, errors="coerce").notna().sum())
            if dropped:
                notes.append(f"{dropped} non-numeric value(s) in '{measure.column}' count as blank")
    return notes


def verify(expr: Expr, df: pd.DataFrame, table: str) -> Verification:
    """
    The gate every KPI passes before it can be exported or shown.

    A KPI is verified only if (a) every column it reads exists with a type its operation
    accepts, (b) the DAX and the expression refer to exactly the same table and columns,
    and (c) computing it on the dataset yields a finite number.
    """
    missing = [c for c in columns_of(expr) if c not in df.columns]
    if missing:
        return Verification(False, f"column(s) not in the dataset: {', '.join(repr(c) for c in missing)}")

    if any(m.group for m in _measures(expr)):
        return Verification(False, "a KPI must be a single value, not one value per group")

    problem = _first_dtype_problem(expr, df)
    if problem:
        return Verification(False, problem)

    try:
        dax = DaxCompiler(table).compile(expr)
    except ValueError as exc:
        return Verification(False, f"could not compile to DAX: {exc}")

    refs = dax_references(dax)
    tables = {t for t, _ in refs} | {t.replace("''", "'") for t in _COUNTROWS_TABLE.findall(dax)}
    if tables != {table} or {c for _, c in refs} != set(columns_of(expr)):
        return Verification(False, "the generated DAX does not match the KPI's columns", dax=dax)

    try:
        value = PandasCompiler().evaluate(expr, df)
    except Exception as exc:  # any failure to compute means the KPI cannot be vouched for
        return Verification(False, f"could not be computed: {exc}", dax=dax)

    if value is None:
        return Verification(False, "result is BLANK (a zero or blank denominator, or no matching rows)", dax=dax)
    if not math.isfinite(value):
        return Verification(False, f"result is not a finite number ({value})", dax=dax)

    note = "; ".join([f"computed on {len(df):,} rows of the cleaned dataset", *_blank_cells(expr, df)])
    return Verification(True, note, value=value, dax=dax)
