"""Plain-English hints for a number that no formula reproduces.

These are *hints*, never matches: they run only after the expected value (what the rule used by
the neighbouring numbers gives here) is known, and they say how the report's number differs from
it: swapped digits, a units slip, off by one, one row or order missing, a category left out.
Nothing here can turn a number into REPRODUCED.
"""

from __future__ import annotations

import itertools
import math
from typing import Optional

import numpy as np

from app.intelligence.kpi.ir import Expr, Filter, Measure, Op
from app.reverse.describe import describe, first_measure
from app.reverse.hypotheses import affinity
from app.reverse.index import DataIndex
from app.reverse.models import TargetCell

_FACTORS = (10.0, 100.0, 1000.0, 1_000_000.0)
MAX_PAIR_ROWS = 300
MAX_CATEGORY_VALUES = 200
MAX_LAST_RESORT_CATEGORIES = 12
_IDENTIFYING = ("order id", "invoice", "transaction", "customer id", "product id", "row id", "id")


def show_value(value: float, target: TargetCell) -> str:
    """A number the way the report would print it (same decimals and unit)."""
    if target.unit == "percent":
        return f"{value * 100:.{target.decimals_shown}f}%"
    if target.scale > 1:
        return f"{value:,.0f}"
    return f"{value:,.{target.decimals_shown}f}"


def _digits(value: float, target: TargetCell) -> str:
    shown = abs(value) / target.scale
    return f"{shown:.{target.decimals_shown}f}".replace(".", "")


def digit_hint(reported: float, expected: float, target: TargetCell) -> Optional[str]:
    a, b = _digits(reported, target), _digits(expected, target)
    if len(a) != len(b) or a == b:
        return None
    differing = [i for i in range(len(a)) if a[i] != b[i]]
    if sorted(a) == sorted(b) and len(differing) == 2:
        return (
            f"two digits look swapped: the data gives {show_value(expected, target)} "
            f"but the report shows {show_value(reported, target)}"
        )
    if len(differing) == 1:
        return (
            f"one digit differs, which looks like a typing mistake: the data gives {show_value(expected, target)} "
            f"but the report shows {show_value(reported, target)}"
        )
    return None


def scale_hint(reported: float, expected: float, target: TargetCell) -> Optional[str]:
    if expected == 0 or reported == 0:
        return None
    ratio = abs(reported / expected)
    for factor in _FACTORS:
        for direction, word in ((factor, f"{factor:,.0f} times"), (1 / factor, f"1/{factor:,.0f} of")):
            if math.isclose(ratio, direction, rel_tol=2e-3):
                return f"the report shows {word} what the data gives ({show_value(expected, target)}); a units or scale slip?"
    return None


def _label_of_row(index: DataIndex, row: int) -> str:
    df = index.df
    for column in df.columns:
        if str(column).casefold() in _IDENTIFYING or str(column).casefold().endswith(" id"):
            return f"{column} {df[column].iloc[row]}"
    return f"row {row + 1}"


def _gap_kind(amount: float, need: float, tol: float) -> Optional[str]:
    """Would ``amount`` explain the gap? ``need`` = data minus report (positive: the report is lower)."""
    if abs(amount - need) <= tol:
        return "left out of the report"  # the report lacks this amount
    if abs(amount + need) <= tol:
        return "counted in the report by mistake"  # the report has this amount extra
    return None


def _sum_like(expr: Expr) -> Optional[Measure]:
    if isinstance(expr, Measure) and (expr.op is Op.COUNT or (expr.op is Op.SUM and expr.column)):
        return expr
    return None


def _scope_values(measure: Measure, index: DataIndex) -> tuple[np.ndarray, np.ndarray, str]:
    scope = np.flatnonzero(index.scope(measure.filters))
    if measure.op is Op.COUNT:
        return scope, np.ones(len(scope)), "rows"
    return scope, np.nan_to_num(index.number_array(measure.column)[scope]), measure.column


def _row_hints(expr: Expr, reported: float, expected: float, tol: float, index: DataIndex, target: TargetCell) -> Optional[str]:
    """The gap equals one row, one whole order/customer/product, or two rows."""
    measure = _sum_like(expr)
    if measure is None:
        return None
    scope, values, what = _scope_values(measure, index)
    if not len(scope):
        return None
    need = expected - reported
    size = show_value(abs(need), target)

    for i, value in enumerate(values):
        kind = _gap_kind(float(value), need, tol)
        if kind:
            return (
                f"the report is {'lower' if need > 0 else 'higher'} than the data by {size}, exactly one row's {what} "
                f"({_label_of_row(index, int(scope[i]))}); that row may have been {kind}"
            )
    for column in index.distinct_columns:
        name = str(column).casefold()
        if not (name.endswith("id") or "order" in name or "invoice" in name):
            continue
        codes, _ = index.categories(column)
        codes = codes[scope]
        present = codes >= 0
        sums = np.bincount(codes[present], weights=values[present])
        counts = np.bincount(codes[present])
        for code in range(len(sums)):
            kind = _gap_kind(float(sums[code]), need, tol) if counts[code] else None
            if kind:
                example = int(scope[np.flatnonzero(codes == code)[0]])
                return (
                    f"the report is {'lower' if need > 0 else 'higher'} than the data by {size}, exactly the {what} of one "
                    f"{column} ({index.df[column].iloc[example]}, {int(counts[code])} row(s)); it may have been {kind}"
                )
    if len(values) <= MAX_PAIR_ROWS:
        for (i, a), (j, b) in itertools.combinations(enumerate(values), 2):
            if _gap_kind(float(a + b), need, tol):
                return (
                    f"the report differs from the data by {size}, which is two rows' {what} together "
                    f"({_label_of_row(index, int(scope[i]))} and {_label_of_row(index, int(scope[j]))})"
                )
    return None


def _category_hint(
    expr: Expr, reported: float, expected: float, tol: float, index: DataIndex, target: TargetCell, only_named: bool
) -> Optional[str]:
    """The report's number equals the data's with one whole category left out.

    ``only_named`` limits this to columns the report's own headings mention ("Region"): leaving out
    a customer or a product is a far more arbitrary explanation, so it is only a last resort.
    """
    measure = _sum_like(expr)
    if measure is None:
        return None
    scope = index.scope(measure.filters)
    filtered = {f.column for f in measure.filters}
    values = np.ones(index.n) if measure.op is Op.COUNT else np.nan_to_num(index.number_array(measure.column))
    named = [*target.row_axis_names, *target.context_labels]
    for column in sorted(index.categorical_columns(), key=lambda c: -affinity(named, c)):  # "Region" heading first
        if column in filtered or column == measure.column:
            continue
        if only_named and affinity(named, column) == 0:
            continue
        codes, names = index.categories(column)
        if not 2 <= len(names) <= (MAX_CATEGORY_VALUES if only_named else MAX_LAST_RESORT_CATEGORIES):
            continue
        keep = scope & (codes >= 0)
        totals = np.bincount(codes[keep], weights=values[keep], minlength=len(names))
        for position, total in enumerate(totals):
            if total != 0 and abs((expected - total) - reported) <= tol:
                return (
                    f"the report equals the data with every row where {column} is {names[position]} left out "
                    f"(the data gives {show_value(expected, target)}); {names[position]} may be missing from the report"
                )
    return None


def difference_text(reported: float, expected: float, target: TargetCell) -> str:
    diff = reported - expected
    if target.unit == "percent":
        return (
            f"the report shows {show_value(reported, target)} but the same rule gives {show_value(expected, target)} "
            f"({diff * 100:+.{max(target.decimals_shown, 1)}f} percentage points)"
        )
    relative = f" ({diff / expected * 100:+.2g}%)" if expected else ""
    return f"the report shows {show_value(reported, target)} but the same rule gives {show_value(expected, target)}, a difference of {diff:+,.{max(target.decimals_shown, 2)}f}{relative}"


def diagnose(target: TargetCell, expected: float, expr: Expr, index: DataIndex) -> str:
    """The most specific explanation we can compute for why ``target`` differs from ``expected``."""
    reported = target.value
    tol = target.tolerance + 1e-9 * max(1.0, abs(reported))
    base = difference_text(reported, expected, target)

    explanation = None
    measure = first_measure(expr)
    if measure is not None and measure.op in (Op.COUNT, Op.DISTINCT_COUNT) and abs(reported - expected) in (1.0, 2.0):
        explanation = f"off by {abs(reported - expected):.0f}: the data gives {show_value(expected, target)}"
    if explanation is None:
        explanation = digit_hint(reported, expected, target) or scale_hint(reported, expected, target)
    if explanation is None:
        explanation = _category_hint(expr, reported, expected, tol, index, target, only_named=True)
    if explanation is None:
        explanation = _row_hints(expr, reported, expected, tol, index, target)
    if explanation is None:
        explanation = _category_hint(expr, reported, expected, tol, index, target, only_named=False)
    rule = describe(expr)
    return f"{explanation[0].upper()}{explanation[1:]}. (Rule: {rule}.)" if explanation else f"{base[0].upper()}{base[1:]}. (Rule: {rule}.)"
