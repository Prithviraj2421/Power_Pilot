"""A searchable view of the raw data: which columns can be measured, filtered, counted, or read as dates.

Everything the synthesizer tries is computed here with numpy over cached boolean masks, so trying
hundreds of formulas per number stays cheap. The numbers are only candidates: whatever is chosen is
recomputed by ``verify()`` (the real DAX/pandas compilers) before it is believed.
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd

from app.common.keyword_match import any_keyword_matches
from app.intelligence.kpi.compilers.pandas_compiler import as_dates, date_part, filter_mask
from app.intelligence.kpi.column_resolver import LABEL_TOKENS
from app.intelligence.kpi.ir import DatePart, Filter, Measure, Op
from app.intelligence.kpi.verification import MIN_NUMERIC_SHARE

MAX_CATEGORIES = 5000  # a text column with more distinct values than this is free text, not a category
MAX_CALENDAR_VALUES = 50
_CALENDAR_NAMES = ("year", "month", "quarter", "qtr", "fy", "period", "week")
_DATE_LOOKING = re.compile(r"^\s*(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}|\d{1,2}[ -][A-Za-z]{3,9}[ -]\d{2,4}|[A-Za-z]{3,9}\.? \d{1,2},? \d{4})")
_MAX_TABLES = 4000  # measure tables kept in memory at once


def normalise(text: object) -> str:
    """Case, punctuation and spacing do not decide whether a label names a value."""
    return " ".join(re.findall(r"[a-z0-9]+", str(text).casefold()))


class DataIndex:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df
        self.n = len(df)
        self.measure_columns: list[str] = []
        self.distinct_columns: list[str] = []
        self.date_columns: list[str] = []
        self.calendar_columns: list[str] = []
        self.date_years: dict[str, tuple[int, int]] = {}
        self.value_index: dict[str, list[tuple[str, object]]] = {}
        self._numbers: dict[str, np.ndarray] = {}
        self._codes: dict[str, np.ndarray] = {}
        self._categories: dict[str, tuple[np.ndarray, list[str]]] = {}
        self._masks: dict[Filter, np.ndarray] = {}
        self._scopes: dict[tuple[Filter, ...], np.ndarray] = {}
        self._tables: dict[tuple[Filter, ...], np.ndarray] = {}
        self._classify()
        self.base_measures: list[Measure] = self._base_measures()

    # --- column roles ---------------------------------------------------------------

    def _classify(self) -> None:
        for column in self.df.columns:
            series = self.df[column]
            if pd.api.types.is_bool_dtype(series):
                continue
            if self._is_date(series):
                self.date_columns.append(column)
                years = as_dates(series).dt.year.dropna()
                if len(years):
                    self.date_years[column] = (int(years.min()), int(years.max()))
                continue
            if pd.api.types.is_numeric_dtype(series):
                if self._is_calendar_part(column, series):
                    self.calendar_columns.append(column)
                    self._index_values(column, series)
                elif not any_keyword_matches(column, LABEL_TOKENS):
                    self.measure_columns.append(column)
                elif pd.api.types.is_integer_dtype(series):
                    self.distinct_columns.append(column)  # Row ID, Postal Code: countable, never summable
                continue
            if self._mostly_numbers(series):
                if not any_keyword_matches(column, LABEL_TOKENS):
                    self.measure_columns.append(column)
                continue
            self.distinct_columns.append(column)
            if series.nunique(dropna=True) <= MAX_CATEGORIES:
                self._index_values(column, series)

    @staticmethod
    def _mostly_numbers(series: pd.Series) -> bool:
        present = int(series.notna().sum())
        if present == 0:
            return False
        return pd.to_numeric(series, errors="coerce").notna().sum() / present >= MIN_NUMERIC_SHARE

    @staticmethod
    def _is_date(series: pd.Series) -> bool:
        if pd.api.types.is_datetime64_any_dtype(series):
            return True
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            return False
        sample = series.dropna().astype(str).head(200)
        if sample.empty or sample.map(lambda s: bool(_DATE_LOOKING.match(s))).mean() < 0.9:
            return False
        parsed = as_dates(series)
        return bool((parsed.notna() | series.isna()).all())  # DAX fails on any text it cannot read as a date

    @staticmethod
    def _is_calendar_part(column: str, series: pd.Series) -> bool:
        if not pd.api.types.is_integer_dtype(series) or series.nunique() > MAX_CALENDAR_VALUES:
            return False
        return any_keyword_matches(column, _CALENDAR_NAMES)

    def _index_values(self, column: str, series: pd.Series) -> None:
        for value in series.dropna().unique():
            original = int(value) if isinstance(value, (int, np.integer)) else str(value)
            key = normalise(original)
            if key:
                entry = self.value_index.setdefault(key, [])
                if (column, original) not in entry:
                    entry.append((column, original))

    def _base_measures(self) -> list[Measure]:
        measures = [Measure(Op.COUNT)]
        for column in self.measure_columns:
            measures += [Measure(op, column) for op in (Op.SUM, Op.AVERAGE, Op.MIN, Op.MAX)]
        measures += [Measure(Op.DISTINCT_COUNT, column) for column in self.distinct_columns]
        return measures

    # --- computing ------------------------------------------------------------------

    def _number_array(self, column: str) -> np.ndarray:
        if column not in self._numbers:
            self._numbers[column] = pd.to_numeric(self.df[column], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        return self._numbers[column]

    def _code_array(self, column: str) -> np.ndarray:
        if column not in self._codes:
            self._codes[column] = pd.factorize(self.df[column])[0]
        return self._codes[column]

    def categories(self, column: str) -> tuple[np.ndarray, list[str]]:
        """Each row's category number (-1 for blank) and the category names, for grouping."""
        if column not in self._categories:
            codes, uniques = pd.factorize(self.df[column])
            self._categories[column] = (codes, [str(u) for u in uniques])
        return self._categories[column]

    def categorical_columns(self) -> list[str]:
        """Columns whose values labels can name (text categories and calendar parts)."""
        return sorted({column for entries in self.value_index.values() for column, _ in entries})

    def number_array(self, column: str) -> np.ndarray:
        return self._number_array(column)

    def mask(self, flt: Filter) -> np.ndarray:
        if flt not in self._masks:
            self._masks[flt] = filter_mask(self.df, flt).to_numpy()
        return self._masks[flt]

    def scope(self, filters: tuple[Filter, ...]) -> np.ndarray:
        """Rows that pass every filter (all rows for no filters)."""
        if filters not in self._scopes:
            combined = np.ones(self.n, dtype=bool)
            for flt in filters:
                combined = combined & self.mask(flt)
            self._scopes[filters] = combined
        return self._scopes[filters]

    def values(self, filters: tuple[Filter, ...]) -> np.ndarray:
        """Every base measure under the filters, in ``base_measures`` order (NaN = BLANK)."""
        cached = self._tables.get(filters)
        if cached is not None:
            return cached
        rows = np.flatnonzero(self.scope(filters))
        out = np.full(len(self.base_measures), np.nan)
        if len(rows):
            for i, measure in enumerate(self.base_measures):
                out[i] = self._aggregate(measure, rows)
        if len(self._tables) >= _MAX_TABLES:
            self._tables.clear()
        self._tables[filters] = out
        return out

    def _aggregate(self, measure: Measure, rows: np.ndarray) -> float:
        if measure.op is Op.COUNT:
            return float(len(rows))
        if measure.op is Op.DISTINCT_COUNT:
            return float(np.unique(self._code_array(measure.column)[rows]).size)
        numbers = self._number_array(measure.column)[rows]
        numbers = numbers[~np.isnan(numbers)]
        if numbers.size == 0:
            return np.nan
        return float({Op.SUM: np.sum, Op.AVERAGE: np.mean, Op.MIN: np.min, Op.MAX: np.max}[measure.op](numbers))

    def value(self, measure: Measure, filters: tuple[Filter, ...]) -> Optional[float]:
        """One base measure under extra filters, or None when it is BLANK."""
        try:
            at = self.base_measures.index(Measure(measure.op, measure.column))
        except ValueError:
            return None
        value = self.values(filters)[at]
        return None if np.isnan(value) else float(value)

    def column_values(self, column: str, filters: tuple[Filter, ...]) -> np.ndarray:
        """The numeric cells of one column in scope (blanks dropped), for 'which row is off' checks."""
        values = self._number_array(column)[self.scope(filters)]
        return values[~np.isnan(values)]

    def date_parts(self, column: str, part: DatePart) -> np.ndarray:
        return date_part(self.df[column], part).to_numpy(dtype=float, na_value=np.nan)
