"""Data shapes for reverse-engineering a legacy report. Everything here is JSON-serialisable."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

Unit = Literal["number", "percent", "currency"]
CellKind = Literal["title", "header", "label", "value", "derived", "other"]


@dataclass(frozen=True)
class DerivedInfo:
    """A number the report computed from other numbers in the same report, not from the data.

    ``op`` is what to re-check (sum/average/min/max over ``sources``); None when the formula is
    something we do not re-compute (it is still shown as derived, with ``formula`` for the reader).
    """

    kind: Literal["formula", "total_label"]
    sources: tuple[str, ...] = ()  # TargetCell ids (or cell ids of non-target numbers)
    op: Optional[Literal["sum", "average", "min", "max"]] = None
    formula: Optional[str] = None


@dataclass(frozen=True)
class TargetCell:
    """One number in the report that PowerPilot has to explain."""

    id: str  # "Sheet1!B3"
    sheet: str
    cell_ref: str  # "B3"
    value: float  # real units: "12.5%" -> 0.125, "1.2M" -> 1_200_000
    shown_text: str
    decimals_shown: int
    unit: Unit
    scale: float  # real size of one displayed unit (0.01 for %, 1e6 for M, ...)
    row_labels: tuple[str, ...]
    col_labels: tuple[str, ...]
    context_labels: tuple[str, ...] = ()  # titles and captions above the table
    row_axis_names: tuple[str, ...] = ()  # headings of the row-label columns, e.g. ("Region",)
    full_precision: bool = False  # True when the file stored the exact value (a spreadsheet number)
    derived: Optional[DerivedInfo] = None

    @property
    def tolerance(self) -> float:
        """Half a unit in the last place the report shows, in real units."""
        return 0.5 * 10 ** (-self.decimals_shown) * self.scale

    @property
    def labels(self) -> tuple[str, ...]:
        """Every label that can describe this number, most specific first."""
        return (*self.row_labels, *self.col_labels, *self.context_labels, *self.row_axis_names)


@dataclass(frozen=True)
class LayoutCell:
    ref: str
    row: int  # 0-based
    col: int
    text: str
    kind: CellKind
    target_id: Optional[str] = None


@dataclass(frozen=True)
class SheetLayout:
    """The report as it looked, so the page can draw it back with each number coloured."""

    name: str
    rows: int
    cols: int
    cells: tuple[LayoutCell, ...]


@dataclass
class ParsedReport:
    targets: list[TargetCell] = field(default_factory=list)
    layout: list[SheetLayout] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
