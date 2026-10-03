"""A small intermediate representation for KPIs.

A KPI used to be a template string such as ``SUM('{tbl}'[Sales_Amount])``, so nothing
could check that the columns existed, or that the formula meant what the KPI name said.
Plugins now build these nodes from columns that really exist in the dataset, and two
independent compilers consume them: one writes DAX for Power BI, the other computes
the value on the cleaned DataFrame. A KPI is only emitted when both agree it is sound.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Union

Scalar = Union[str, int, float, bool]


class Op(StrEnum):
    SUM = "sum"
    COUNT = "count"  # non-blank values of a column, or rows when no column is given
    DISTINCT_COUNT = "distinct_count"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    RATIO = "ratio"


class Compare(StrEnum):
    EQ = "=="
    NE = "!="
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="
    IN = "in"


_NEEDS_COLUMN = {Op.SUM, Op.DISTINCT_COUNT, Op.AVERAGE, Op.MIN, Op.MAX}


@dataclass(frozen=True)
class Filter:
    """Restrict a measure to rows where ``column <compare> value`` (a tuple for ``IN``)."""

    column: str
    compare: Compare
    value: Union[Scalar, tuple[Scalar, ...]]

    def __post_init__(self) -> None:
        if (self.compare is Compare.IN) != isinstance(self.value, tuple):
            raise ValueError("an IN filter takes a tuple of values; every other comparison takes one value")


@dataclass(frozen=True)
class Measure:
    """One aggregation of one column, optionally filtered and/or grouped."""

    op: Op
    column: Optional[str] = None
    filter: Optional[Filter] = None
    group: Optional[str] = None

    def __post_init__(self) -> None:
        if self.op is Op.RATIO:
            raise ValueError("a Measure aggregates a column; use Ratio to divide two expressions")
        if self.op in _NEEDS_COLUMN and not self.column:
            raise ValueError(f"{self.op.value} needs a column")


@dataclass(frozen=True)
class Ratio:
    """``numerator / denominator * scale``. BLANK when the denominator is zero or blank."""

    numerator: "Expr"
    denominator: "Expr"
    scale: float = 1.0

    @property
    def op(self) -> Op:
        return Op.RATIO


@dataclass(frozen=True)
class Difference:
    """``minuend - subtrahend``, e.g. revenue less expenses."""

    minuend: "Expr"
    subtrahend: "Expr"


Expr = Union[Measure, Ratio, Difference]


def columns_of(expr: Expr) -> tuple[str, ...]:
    """Every dataset column an expression reads, in first-use order, without repeats."""
    found: list[str] = []

    def walk(node: Expr) -> None:
        if isinstance(node, Measure):
            for name in (node.column, node.filter.column if node.filter else None, node.group):
                if name and name not in found:
                    found.append(name)
        elif isinstance(node, Ratio):
            walk(node.numerator)
            walk(node.denominator)
        else:
            walk(node.minuend)
            walk(node.subtrahend)

    walk(expr)
    return tuple(found)


def total(column: str) -> Measure:
    return Measure(Op.SUM, column)


def average(column: str) -> Measure:
    return Measure(Op.AVERAGE, column)


def distinct(column: str) -> Measure:
    return Measure(Op.DISTINCT_COUNT, column)
