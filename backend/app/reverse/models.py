"""Data shapes for reverse-engineering a legacy report. Everything here is JSON-serialisable."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from app.intelligence.kpi.ir import Expr

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
    block: int = 0  # which table on the sheet (tables are separated by blank rows)

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


# --- results ------------------------------------------------------------------------------

REPRODUCED = "REPRODUCED"
AMBIGUOUS = "AMBIGUOUS"
NOT_REPRODUCIBLE = "NOT_REPRODUCIBLE"
DERIVED = "DERIVED"


@dataclass
class Alternative:
    """Another formula that also fits the number."""

    formula: str
    dax: Optional[str]
    value: float
    expr: Optional[Expr] = None  # kept for migration; not part of the JSON


@dataclass
class Closest:
    """What the rule used by the neighbouring numbers gives here, when nothing fits the number itself."""

    value: float
    formula: str
    difference: float  # reported minus recomputed
    relative: Optional[float]  # difference / recomputed
    expr: Optional[Expr] = None


@dataclass
class DerivedCheck:
    consistent: bool  # the report's number equals what its own parts give
    expected: Optional[float]
    explanation: str
    data_value: Optional[float] = None  # what the raw data gives for the same cell, when we could work it out
    matches_data: Optional[bool] = None  # None when the data could not be consulted


@dataclass
class CellResult:
    target: TargetCell
    status: str
    basis: Optional[str] = None  # "raw" | "cleaned"
    expr: Optional[Expr] = None
    formula: str = ""
    dax: Optional[str] = None
    recomputed: Optional[float] = None
    exact: bool = False  # matched the stored full-precision value, not just the shown digits
    evidence: Optional[str] = None  # strong | moderate | weak
    reasons: list[str] = field(default_factory=list)
    alternatives: list[Alternative] = field(default_factory=list)
    closest: Optional[Closest] = None
    hint: Optional[str] = None
    notes: list[str] = field(default_factory=list)
    derived_check: Optional[DerivedCheck] = None
    shape: Optional[str] = None
    proposed_by: Optional[str] = None  # set when a language model suggested the formula (computation still proved it)

    @property
    def writable(self) -> bool:
        """Only a formula proven on the raw data may become a measure in the model."""
        return self.status == REPRODUCED and self.basis == "raw" and self.expr is not None

    def to_dict(self) -> dict:
        from app.reverse.describe import ir_to_dict

        return {
            "id": self.target.id,
            "status": self.status,
            "basis": self.basis,
            "target": target_to_dict(self.target),
            "formula": self.formula,
            "ir": ir_to_dict(self.expr) if self.expr is not None else None,
            "dax": self.dax,
            "recomputed": self.recomputed,
            "exact": self.exact,
            "evidence": self.evidence,
            "reasons": self.reasons,
            "alternatives": [{"formula": a.formula, "dax": a.dax, "value": a.value} for a in self.alternatives],
            "closest": None
            if self.closest is None
            else {
                "value": self.closest.value,
                "formula": self.closest.formula,
                "difference": self.closest.difference,
                "relative": self.closest.relative,
            },
            "hint": self.hint,
            "notes": self.notes,
            "derived_check": None
            if self.derived_check is None
            else {
                "consistent": self.derived_check.consistent,
                "expected": self.derived_check.expected,
                "explanation": self.derived_check.explanation,
                "data_value": self.derived_check.data_value,
                "matches_data": self.derived_check.matches_data,
            },
            "writable": self.writable,
            "proposed_by": self.proposed_by,
        }


def target_to_dict(target: TargetCell) -> dict:
    return {
        "id": target.id,
        "sheet": target.sheet,
        "cell_ref": target.cell_ref,
        "value": target.value,
        "shown_text": target.shown_text,
        "decimals_shown": target.decimals_shown,
        "unit": target.unit,
        "row_labels": list(target.row_labels),
        "col_labels": list(target.col_labels),
        "context_labels": list(target.context_labels),
        "derived": None
        if target.derived is None
        else {"kind": target.derived.kind, "op": target.derived.op, "sources": list(target.derived.sources), "formula": target.derived.formula},
    }


@dataclass
class ReverseSummary:
    cells: int
    reproduced: int
    ambiguous: int
    not_reproducible: int
    derived: int
    percent_reproduced: float  # of the numbers that had to come from the data (derived ones excluded)
    suspected_errors: int
    seconds: float
    budget_exhausted: bool = False


@dataclass
class ReverseReport:
    report_id: str
    filename: str
    table: str
    results: list[CellResult]
    layout: list[SheetLayout]
    warnings: list[str]
    summary: ReverseSummary
    rows_analysed: int = 0
    plan: Optional[Any] = None  # a MigrationPlan: the measures the proven numbers can become
    dataset_id: Optional[str] = None  # the registered upload this was run against (None for a live model)
    live: bool = False  # run against a table of the open Power BI model
    rows_total: int = 0  # rows the table held when it was analysed
    sampled: bool = False  # only part of the table was read, so nothing may be written back

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "filename": self.filename,
            "table": self.table,
            "rows_analysed": self.rows_analysed,
            "rows_total": self.rows_total,
            "sampled": self.sampled,
            "live": self.live,
            "dataset_id": self.dataset_id,
            "plan": self.plan.to_dict() if self.plan is not None else None,
            "summary": self.summary.__dict__,
            "warnings": self.warnings,
            "cells": [r.to_dict() for r in self.results],
            "layout": [
                {
                    "name": sheet.name,
                    "rows": sheet.rows,
                    "cols": sheet.cols,
                    "cells": [
                        {"ref": c.ref, "row": c.row, "col": c.col, "text": c.text, "kind": c.kind, "target_id": c.target_id}
                        for c in sheet.cells
                    ],
                }
                for sheet in self.layout
            ],
        }
