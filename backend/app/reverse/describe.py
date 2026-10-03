"""Formulas in plain words, as JSON, and as an abstract "shape".

The *shape* of a formula is the formula with its filter values left out
(``SUM(Sales) where Region = * and YEAR(Order Date) = *``). Cells of one report that follow the same
rule have the same shape, which is what lets neighbours settle a cell the numbers alone cannot.
"""

from __future__ import annotations

from typing import Optional

from app.intelligence.kpi.ir import Compare, DatePart, Difference, Expr, Filter, Measure, Op, Ratio

_OP_WORDS = {
    Op.SUM: "Sum of {c}",
    Op.AVERAGE: "Average of {c}",
    Op.MIN: "Smallest {c}",
    Op.MAX: "Largest {c}",
    Op.DISTINCT_COUNT: "Number of different {c}",
    Op.COUNT: "Number of non-blank {c}",
}
_COMPARE_WORDS = {
    Compare.EQ: "is",
    Compare.NE: "is not",
    Compare.GT: "is above",
    Compare.GE: "is at least",
    Compare.LT: "is below",
    Compare.LE: "is at most",
    Compare.IN: "is one of",
}
_PART_WORDS = {DatePart.YEAR: "year", DatePart.QUARTER: "quarter", DatePart.MONTH: "month"}


def _value(value: object) -> str:
    if isinstance(value, tuple):
        return ", ".join(_value(v) for v in value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def describe_filter(flt: Filter) -> str:
    subject = f"the {_PART_WORDS[flt.part]} of {flt.column}" if flt.part else flt.column
    return f"{subject} {_COMPARE_WORDS[flt.compare]} {_value(flt.value)}"


def _measure_words(measure: Measure) -> str:
    if measure.op is Op.COUNT and measure.column is None:
        text = "Number of rows"
    else:
        text = _OP_WORDS[measure.op].format(c=measure.column)
    if measure.filters:
        text += " where " + " and ".join(describe_filter(f) for f in measure.filters)
    return text


def describe(expr: Expr) -> str:
    """One sentence a business user can check against the report."""
    if isinstance(expr, Measure):
        return _measure_words(expr)
    if isinstance(expr, Ratio):
        text = f"{describe(expr.numerator)}, divided by {describe(expr.denominator)}"
        return text if expr.scale == 1 else f"{text} (times {expr.scale:g})"
    return f"{describe(expr.minuend)}, minus {describe(expr.subtrahend)}"


def _filter_dict(flt: Filter) -> dict:
    out = {"column": flt.column, "compare": flt.compare.value, "value": list(flt.value) if isinstance(flt.value, tuple) else flt.value}
    if flt.part:
        out["part"] = flt.part.value
    return out


def ir_to_dict(expr: Expr) -> dict:
    """The expression as plain JSON (what the page shows as 'the formula')."""
    if isinstance(expr, Measure):
        out: dict = {"type": "measure", "op": expr.op.value, "column": expr.column}
        if expr.filters:
            out["filters"] = [_filter_dict(f) for f in expr.filters]
        return out
    if isinstance(expr, Ratio):
        return {"type": "ratio", "numerator": ir_to_dict(expr.numerator), "denominator": ir_to_dict(expr.denominator), "scale": expr.scale}
    return {"type": "difference", "minuend": ir_to_dict(expr.minuend), "subtrahend": ir_to_dict(expr.subtrahend)}


def _filter_shape(flt: Filter) -> str:
    subject = f"{flt.part.value}({flt.column})" if flt.part else flt.column
    return f"{subject}{flt.compare.value}*"


def shape_of(expr: Expr) -> str:
    """The formula with every filter value replaced by ``*``; equal for cells following one rule."""
    if isinstance(expr, Measure):
        body = f"{expr.op.value}({expr.column or ''})"
        if expr.filters:
            body += "[" + ",".join(sorted(_filter_shape(f) for f in expr.filters)) + "]"
        return body
    if isinstance(expr, Ratio):
        return f"({shape_of(expr.numerator)})/({shape_of(expr.denominator)})x{expr.scale:g}"
    return f"({shape_of(expr.minuend)})-({shape_of(expr.subtrahend)})"


def filters_of(expr: Expr) -> tuple[Filter, ...]:
    """Every filter an expression applies (numerator side first)."""
    if isinstance(expr, Measure):
        return expr.filters
    if isinstance(expr, Ratio):
        return (*filters_of(expr.numerator), *filters_of(expr.denominator))
    return (*filters_of(expr.minuend), *filters_of(expr.subtrahend))


def canonical_filters(filters: tuple[Filter, ...]) -> tuple[Filter, ...]:
    """A stable order, so equal filter sets compare and cache as equal."""
    return tuple(sorted(filters, key=lambda f: (f.column, f.part.value if f.part else "", f.compare.value, repr(f.value))))


def first_measure(expr: Expr) -> Optional[Measure]:
    if isinstance(expr, Measure):
        return expr
    if isinstance(expr, Ratio):
        return first_measure(expr.numerator)
    return first_measure(expr.minuend)
