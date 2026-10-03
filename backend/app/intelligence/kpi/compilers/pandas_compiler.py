from __future__ import annotations

import math
from typing import Optional

import pandas as pd

from app.common.date_parse import parse_dates_robust
from app.intelligence.kpi.ir import Compare, DatePart, Expr, Filter, Measure, Op, Ratio


def _blank_if_nan(value: float) -> Optional[float]:
    return None if value is None or math.isnan(value) else float(value)


def as_dates(series: pd.Series) -> pd.Series:
    """A date column as datetimes: already-parsed columns as they are, text via ``parse_dates_robust``."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return parse_dates_robust(series)


def date_part(series: pd.Series, part: DatePart) -> pd.Series:
    """The year, quarter or month of each date (NaN where the cell is blank or not a date)."""
    dates = as_dates(series).dt
    return {DatePart.YEAR: dates.year, DatePart.QUARTER: dates.quarter, DatePart.MONTH: dates.month}[part]


def filter_mask(df: pd.DataFrame, flt: Filter) -> pd.Series:
    """Rows a filter keeps. Blank cells never pass (DAX does not match them either)."""
    column = date_part(df[flt.column], flt.part) if flt.part is not None else df[flt.column]
    if flt.compare is Compare.IN:
        mask = column.isin(flt.value)
    elif flt.compare is Compare.EQ:
        mask = column == flt.value
    elif flt.compare is Compare.NE:
        mask = column != flt.value
    else:
        numbers = pd.to_numeric(column, errors="coerce")
        mask = {
            Compare.GT: numbers > flt.value,
            Compare.GE: numbers >= flt.value,
            Compare.LT: numbers < flt.value,
            Compare.LE: numbers <= flt.value,
        }[flt.compare]
    return mask.fillna(False).astype(bool)


class PandasCompiler:
    """
    Evaluates KPI expressions on a DataFrame using DAX's rules, so the result is what the
    exported measure returns in Power BI (given the same, cleaned, data):

    * numeric aggregates ignore blanks, and text that is not a number counts as blank
      (the Power Query script blanks cells that fail its type cast);
    * ``DISTINCTCOUNT`` counts BLANK as a value; any aggregate over an empty scope is BLANK;
    * ``DIVIDE`` is BLANK when the denominator is zero or blank, or the numerator is blank;
    * in ``-``, a BLANK operand acts as 0 unless both are BLANK.

    ``None`` stands for BLANK throughout.
    """

    def evaluate(self, expr: Expr, df: pd.DataFrame) -> Optional[float]:
        if isinstance(expr, Measure):
            if expr.group:
                raise ValueError("a grouped measure has one value per group; use evaluate_grouped")
            return self._measure(expr, df)
        if isinstance(expr, Ratio):
            numerator = self.evaluate(expr.numerator, df)
            denominator = self.evaluate(expr.denominator, df)
            if numerator is None or denominator is None or denominator == 0:
                return None
            return numerator / denominator * expr.scale
        left = self.evaluate(expr.minuend, df)
        right = self.evaluate(expr.subtrahend, df)
        if left is None and right is None:
            return None
        return (left or 0.0) - (right or 0.0)

    def evaluate_grouped(self, measure: Measure, df: pd.DataFrame) -> dict[object, Optional[float]]:
        if not measure.group:
            raise ValueError("evaluate_grouped needs a grouped measure")
        scoped = self._scope(df, measure.filters)
        plain = Measure(measure.op, measure.column)
        return {key: self._measure(plain, part) for key, part in scoped.groupby(measure.group, dropna=False)}

    def _measure(self, measure: Measure, df: pd.DataFrame) -> Optional[float]:
        scoped = self._scope(df, measure.filters)
        if len(scoped) == 0:
            return None
        if measure.op is Op.COUNT and measure.column is None:
            return float(len(scoped))
        series = scoped[measure.column]
        if measure.op is Op.COUNT:
            return float(series.notna().sum())
        if measure.op is Op.DISTINCT_COUNT:
            return float(series.nunique(dropna=False))
        numbers = pd.to_numeric(series, errors="coerce").dropna()
        if numbers.empty:
            return None
        aggregate = {Op.SUM: numbers.sum, Op.AVERAGE: numbers.mean, Op.MIN: numbers.min, Op.MAX: numbers.max}
        return _blank_if_nan(aggregate[measure.op]())

    @staticmethod
    def _scope(df: pd.DataFrame, filters: tuple[Filter, ...]) -> pd.DataFrame:
        for flt in filters:
            df = df[filter_mask(df, flt)]
        return df
