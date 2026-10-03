"""Search for the formulas that explain a number. Computation decides; labels only choose what to try.

For one target number we enumerate formulas implied by its labels (filters named by the row/column
headers, the measure the words mention), compute each on the raw data, and keep those that land
inside what the report *shows* (half a unit in the last printed digit). If no formula using every
label fits, labels are dropped one at a time and the loss is recorded; if still nothing fits, ratios
and differences are tried. Several different formulas fitting one number is not a failure to hide:
those are returned side by side, and neighbouring cells settle which one the report author meant.
"""

from __future__ import annotations

import itertools
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app.intelligence.kpi.ir import Difference, Expr, Filter, Measure, Op, Ratio
from app.reverse.describe import canonical_filters, shape_of
from app.reverse.hypotheses import FilterOption, Hints, LabelReader
from app.reverse.index import DataIndex
from app.reverse.models import TargetCell

MAX_FILTER_SETS = 300  # per target, across every relaxation level
MAX_CANDIDATES = 40  # shapes kept per target
AMBIGUITY_MARGIN = 1.0  # shapes scoring within this of the best are genuine alternatives; the rest are long shots
_RATIO_OPS = {Op.SUM, Op.COUNT, Op.DISTINCT_COUNT}
FALLBACK_MIN_DIGITS = 4  # below this, a ratio or difference fitting by chance is too likely to be believed


@dataclass
class Candidate:
    expr: Expr
    value: float
    shape: str
    score: float
    kind: str  # direct | ratio | difference
    used: tuple[str, ...] = ()  # labels applied as filters
    dropped: tuple[str, ...] = ()  # labels that named a filter but were left out to make it fit
    reasons: list[str] = field(default_factory=list)


@dataclass
class CellSearch:
    target: TargetCell
    hints: Hints
    candidates: list[Candidate] = field(default_factory=list)  # one per shape, best first
    tried: int = 0
    exhausted: bool = False  # the time budget ran out before the search finished


def significant_digits(target: TargetCell) -> int:
    digits = re.sub(r"\D", "", re.sub(r"[A-Za-z]+\.?$", "", target.shown_text))
    return max(1, len(digits.lstrip("0")))


def tolerance_for(target: TargetCell) -> float:
    return target.tolerance + 1e-9 * max(1.0, abs(target.value))


class Synthesizer:
    def __init__(self, index: DataIndex, *, max_filter_sets: int = MAX_FILTER_SETS) -> None:
        self.index = index
        self.reader = LabelReader(index)
        self.max_filter_sets = max_filter_sets
        ops = np.array([m.op in _RATIO_OPS for m in index.base_measures])
        sums = np.array([m.op is Op.SUM for m in index.base_measures])
        self._ratio_rows = np.flatnonzero(ops)
        self._sum_rows = np.flatnonzero(sums)

    # --- public ---------------------------------------------------------------------

    def search(self, target: TargetCell, deadline: Optional[float] = None) -> CellSearch:
        hints = self.reader.hints_for(target)
        result = CellSearch(target, hints)
        found: dict[str, Candidate] = {}
        tol = tolerance_for(target)

        for fallback in (False, True):
            if fallback and (found or significant_digits(target) < FALLBACK_MIN_DIGITS):
                break
            tried_here = 0
            for size in range(len(hints.slots), -1, -1):
                for chosen in itertools.combinations(range(len(hints.slots)), size):
                    dropped = tuple(hints.slots[i].label for i in range(len(hints.slots)) if i not in chosen)
                    used = tuple(hints.slots[i].label for i in chosen)
                    for options in itertools.product(*(hints.slots[i].options for i in chosen)):
                        if deadline is not None and time.monotonic() > deadline:
                            result.exhausted = True
                            break
                        if tried_here >= self.max_filter_sets:
                            break
                        tried_here += 1
                        filters = self._merge(options)
                        if filters is None:
                            continue
                        self._match(target, hints, filters, options, used, dropped, tol, found, fallback)
                    if result.exhausted or tried_here >= self.max_filter_sets:
                        break
                if found or result.exhausted or tried_here >= self.max_filter_sets:
                    break
            result.tried += tried_here
            if result.exhausted:
                break

        ranked = sorted(found.values(), key=lambda c: (-c.score, c.shape))
        result.candidates = ranked[:MAX_CANDIDATES]
        return result

    # --- one filter set -------------------------------------------------------------

    @staticmethod
    def _merge(options: tuple[FilterOption, ...]) -> Optional[tuple[Filter, ...]]:
        filters: list[Filter] = []
        for option in options:
            for flt in option.filters:
                if flt not in filters:
                    filters.append(flt)
        return canonical_filters(tuple(filters))

    def _match(
        self,
        target: TargetCell,
        hints: Hints,
        filters: tuple[Filter, ...],
        options: tuple[FilterOption, ...],
        used: tuple[str, ...],
        dropped: tuple[str, ...],
        tol: float,
        found: dict[str, Candidate],
        fallback: bool,
    ) -> None:
        index = self.index
        values = index.values(filters)
        filter_bonus = 0.5 * sum(o.affinity for o in options) - 0.1 * len(filters) - 3.0 * len(dropped)
        reasons_base = [f"label '{label}' was not used as a filter" for label in dropped]

        if not fallback:
            hits = np.flatnonzero(np.abs(values - target.value) <= tol)
            for i in hits:
                measure = index.base_measures[i]
                expr = Measure(measure.op, measure.column, filters)
                score = 10 + filter_bonus + self._measure_bonus(hints, measure, "direct")
                self._keep(found, Candidate(expr, float(values[i]), shape_of(expr), score, "direct", used, dropped, list(reasons_base)))

        if hints.ratio or fallback:
            self._ratios(target, hints, filters, values, tol, used, dropped, filter_bonus, reasons_base, found)
        if hints.difference or fallback:
            self._differences(target, hints, filters, values, tol, used, dropped, filter_bonus, reasons_base, found)

    def _ratios(self, target, hints, filters, values, tol, used, dropped, filter_bonus, reasons_base, found) -> None:
        index = self.index
        rows = self._ratio_rows
        numerators = values[rows]
        scales = (1.0, 100.0) if target.unit != "percent" else (1.0,)
        subsets = [filters] if len(filters) > 3 else [
            canonical_filters(tuple(c)) for r in range(len(filters), -1, -1) for c in itertools.combinations(filters, r)
        ]
        for denominator_filters in subsets:
            denominators = index.values(denominator_filters)[rows]
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = numerators[:, None] / denominators[None, :]
            ratio[~np.isfinite(ratio)] = np.nan
            if denominator_filters == filters:
                np.fill_diagonal(ratio, np.nan)  # x / x is always 1
            for scale in scales:
                hits = np.argwhere(np.abs(ratio * scale - target.value) <= tol)
                for i, j in hits:
                    top, bottom = index.base_measures[rows[i]], index.base_measures[rows[j]]
                    expr = Ratio(
                        Measure(top.op, top.column, filters),
                        Measure(bottom.op, bottom.column, denominator_filters),
                        scale,
                    )
                    score = 10 + filter_bonus + self._measure_bonus(hints, top, "ratio") + self._measure_bonus(hints, bottom, "ratio") - 1.0
                    if denominator_filters != filters:
                        score -= 0.2
                    self._keep(found, Candidate(expr, float(ratio[i, j] * scale), shape_of(expr), score, "ratio", used, dropped, list(reasons_base)))

    def _differences(self, target, hints, filters, values, tol, used, dropped, filter_bonus, reasons_base, found) -> None:
        rows = self._sum_rows
        sums = values[rows]
        gap = sums[:, None] - sums[None, :]
        hits = np.argwhere(np.abs(gap - target.value) <= tol)
        for i, j in hits:
            if i == j:
                continue
            first, second = self.index.base_measures[rows[i]], self.index.base_measures[rows[j]]
            expr = Difference(Measure(first.op, first.column, filters), Measure(second.op, second.column, filters))
            score = 10 + filter_bonus + self._measure_bonus(hints, first, "difference") + self._measure_bonus(hints, second, "difference") - 1.5
            self._keep(found, Candidate(expr, float(gap[i, j]), shape_of(expr), score, "difference", used, dropped, list(reasons_base)))

    # --- scoring --------------------------------------------------------------------

    @staticmethod
    def _measure_bonus(hints: Hints, measure: Measure, kind: str) -> float:
        bonus = 0.0
        if measure.column:
            bonus += 2.0 * hints.column_affinity(measure.column)
            if measure.op is Op.DISTINCT_COUNT and re.search(r"\b(id|code|key)\b", measure.column.casefold()):
                bonus += 0.2  # only orders alternatives; never decides between them
        if kind == "direct" and measure.op in hints.ops:
            bonus += 1.0
        return bonus

    @staticmethod
    def _keep(found: dict[str, Candidate], candidate: Candidate) -> None:
        current = found.get(candidate.shape)
        if current is None or candidate.score > current.score:
            found[candidate.shape] = candidate
