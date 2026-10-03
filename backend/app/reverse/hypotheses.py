"""What a report's own words say about its formulas.

A cell under "West" in a table headed "Sales by Region" and "2024" is, most likely, sales where
Region is West and the year is 2024. This module turns those words into *hypotheses*: filters the
labels name (a value in the data, a year, a quarter, a month) and hints about the measure (the
column mentioned, "average", "count", "margin %"). Hypotheses only decide what to try and in which
order; whether a formula is believed is decided by computing it.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from typing import Optional

from app.intelligence.kpi.ir import Compare, DatePart, Filter, Op
from app.reverse.index import DataIndex, normalise
from app.reverse.models import TargetCell

_GENERIC_COLUMN_WORDS = {"id", "name", "no", "number", "code", "date", "amount", "value", "total", "count", "key"}
_NOT_VALUES = {"total", "all", "sum", "average", "avg", "mean", "count", "number", "grand", "subtotal", "overall"}
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4, "may": 5,
    "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_AVERAGE_WORDS = {"average", "avg", "mean"}
_SUM_WORDS = {"total", "sum"}
_COUNT_WORDS = {"count", "number", "orders", "customers", "clients", "users", "products", "items", "transactions", "unique", "distinct", "headcount", "qty"}
_MAX_WORDS = {"max", "maximum", "highest", "largest", "peak"}
_MIN_WORDS = {"min", "minimum", "lowest", "smallest"}
_RATIO_WORDS = {"margin", "rate", "ratio", "share", "percent", "percentage", "pct", "per", "proportion", "mix"}
_DIFFERENCE_WORDS = {"net", "difference", "diff", "variance", "less", "minus", "gap"}
MAX_OPTIONS = 16


def stem(token: str) -> str:
    token = token.casefold()
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def _column_words(column: str) -> set[str]:
    words = {stem(t) for t in _tokens(column)}
    specific = {w for w in words if w not in _GENERIC_COLUMN_WORDS}
    return specific or words


def affinity(texts: list[str], column: str) -> float:
    """How much of a column's name (its distinctive words) the given texts mention, 0..1."""
    wanted = _column_words(column)
    if not wanted:
        return 0.0
    mentioned = {stem(t) for text in texts for t in _tokens(text)}
    return len(wanted & mentioned) / len(wanted)


@dataclass(frozen=True)
class FilterOption:
    """One way a label could restrict the data: all of ``filters`` together."""

    filters: tuple[Filter, ...]
    affinity: float = 0.0  # how much the cell's words point at the filtered column


@dataclass(frozen=True)
class LabelHint:
    label: str
    options: tuple[FilterOption, ...]  # alternatives; empty when the label names no filter


@dataclass
class Hints:
    slots: list[LabelHint] = field(default_factory=list)  # labels that name a filter
    words: list[str] = field(default_factory=list)  # every label, for column affinity
    ops: set[Op] = field(default_factory=set)
    ratio: bool = False
    percent: bool = False
    difference: bool = False

    def column_affinity(self, column: str) -> float:
        return affinity(self.words, column)


class LabelReader:
    """Interprets labels against one dataset; caches per label."""

    def __init__(self, index: DataIndex) -> None:
        self.index = index
        self._cache: dict[tuple[str, tuple[str, ...]], LabelHint] = {}

    def hints_for(self, target: TargetCell) -> Hints:
        axis = list(target.row_axis_names)
        hints = Hints(words=[*target.labels])
        for label in (*target.row_labels, *target.col_labels, *target.context_labels):
            hint = self.read(label, tuple(axis))
            if hint.options:
                hints.slots.append(hint)
        tokens = {t for label in target.labels for t in _tokens(label)}
        raw = " ".join(target.labels)
        if tokens & _AVERAGE_WORDS:
            hints.ops.add(Op.AVERAGE)
        if tokens & _SUM_WORDS:
            hints.ops.add(Op.SUM)
        if tokens & _COUNT_WORDS or "#" in raw:
            hints.ops |= {Op.DISTINCT_COUNT, Op.COUNT}
        if tokens & _MAX_WORDS:
            hints.ops.add(Op.MAX)
        if tokens & _MIN_WORDS:
            hints.ops.add(Op.MIN)
        hints.percent = target.unit == "percent" or "%" in raw
        hints.ratio = hints.percent or bool(tokens & _RATIO_WORDS)
        hints.difference = bool(tokens & _DIFFERENCE_WORDS)
        return hints

    def read(self, label: str, axis: tuple[str, ...]) -> LabelHint:
        key = (label, axis)
        if key not in self._cache:
            self._cache[key] = self._read(label, axis)
        return self._cache[key]

    # --- one label ------------------------------------------------------------------

    def _read(self, label: str, axis: tuple[str, ...]) -> LabelHint:
        tokens = _tokens(label)
        parts: list[list[FilterOption]] = []
        date_options, date_tokens = self._date_options(label, tokens, axis)
        if date_options:
            parts.append(date_options)
        position = 0
        while position < len(tokens):
            hit = self._value_at(tokens, position)
            if hit is None:
                position += 1
                continue
            length, entries = hit
            options = [
                FilterOption((Filter(column, Compare.EQ, value),), affinity([label, *axis], column))
                for column, value in entries
            ]
            if date_options and length == 1 and position in date_tokens:
                date_options.extend(options)  # "2024" is a year in a date column or a value in a Year column: alternatives
            else:
                parts.append(options)
            position += length
        if not parts:
            return LabelHint(label, ())
        combos = itertools.islice(itertools.product(*parts), MAX_OPTIONS)
        options = [
            FilterOption(
                tuple(f for option in combo for f in option.filters),
                max(option.affinity for option in combo),
            )
            for combo in combos
        ]
        return LabelHint(label, tuple(options))

    def _value_at(self, tokens: list[str], start: int) -> Optional[tuple[int, list[tuple[str, object]]]]:
        for length in range(min(4, len(tokens) - start), 0, -1):
            words = tokens[start : start + length]
            phrase = " ".join(words)
            if length == 1 and (phrase in _NOT_VALUES or (len(phrase) < 2 and len(tokens) > 1)):
                continue
            if all(w in _NOT_VALUES for w in words):
                continue
            entries = self.index.value_index.get(phrase)
            if entries:
                return length, entries
        return None

    def _date_options(
        self, label: str, tokens: list[str], axis: tuple[str, ...]
    ) -> tuple[list[FilterOption], set[int]]:
        """Year/quarter/month filters on each date column, and which tokens produced them."""
        if not self.index.date_columns:
            return [], set()
        year = quarter = month = None
        used: set[int] = set()
        compact = label.strip()
        if match := re.fullmatch(r"(\d{4})[-/](\d{1,2})", compact):
            year, month = int(match.group(1)), int(match.group(2))
            used = set(range(len(tokens)))
        elif match := re.fullmatch(r"(\d{1,2})[-/](\d{4})", compact):
            month, year = int(match.group(1)), int(match.group(2))
            used = set(range(len(tokens)))
        else:
            for i, token in enumerate(tokens):
                if re.fullmatch(r"(?:fy)?(\d{4})", token) and year is None:
                    year = int(token[-4:])
                    used.add(i)
                elif re.fullmatch(r"q[1-4]", token) and quarter is None:
                    quarter = int(token[1])
                    used.add(i)
                elif token in _MONTHS and month is None:
                    month = _MONTHS[token]
                    used.add(i)
                    follower = tokens[i + 1] if i + 1 < len(tokens) else ""
                    if re.fullmatch(r"\d{2}", follower) and year is None:
                        year = 2000 + int(follower)
                        used.add(i + 1)
        if month is not None and not 1 <= month <= 12:
            return [], set()
        if year is None and quarter is None and month is None:
            return [], set()
        options = []
        for column in self.index.date_columns:
            low, high = self.index.date_years.get(column, (0, 9999))
            if year is not None and not low <= year <= high:
                continue
            filters = []
            if year is not None:
                filters.append(Filter(column, Compare.EQ, year, DatePart.YEAR))
            if quarter is not None:
                filters.append(Filter(column, Compare.EQ, quarter, DatePart.QUARTER))
            if month is not None:
                filters.append(Filter(column, Compare.EQ, month, DatePart.MONTH))
            options.append(FilterOption(tuple(filters), affinity([label, *axis], column)))
        return options, used
