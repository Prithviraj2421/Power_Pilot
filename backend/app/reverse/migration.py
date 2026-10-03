"""From proven numbers to measures: group cells that follow one rule, name them, and keep every check.

Forty cells of a report that all read "sales for one region in one year" do not need forty measures:
one ``Total Sales`` measure, sliced by Region and Year in a visual, reproduces every one of them.
The grouped measure drops the filters that vary from cell to cell (the visual supplies those) and
keeps the ones that never change. It is only offered because each cell's *explicit* formula was
proven; each of those, and the measure itself, is run through Power BI's own engine before anything
is written.

Only cells proven on the raw data (``CellResult.writable``) take part.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from app.intelligence.kpi.compilers import DaxCompiler
from app.intelligence.kpi.ir import Difference, Expr, Filter, Measure, Op, Ratio
from app.reverse.describe import canonical_filters, describe, filters_of
from app.reverse.models import CellResult

DISPLAY_FOLDER = "PowerPilot\\Migrated"  # TOM nests display folders with a backslash
MAX_NAME_LENGTH = 100


@dataclass(frozen=True)
class MeasureCheck:
    """One thing Power BI's engine must agree with before a measure is written."""

    label: str
    dax: str
    expected: float
    cell_id: Optional[str] = None


@dataclass
class MigratedMeasure:
    id: str
    name: str
    kind: str  # "single" | "grouped"
    expr: Expr
    dax: str
    description: str
    cell_ids: list[str]
    checks: list[MeasureCheck] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    display_folder: str = DISPLAY_FOLDER
    axes: list[str] = field(default_factory=list)  # what the visual must slice a grouped measure by
    filename: str = ""

    def refresh(self) -> None:
        """Rewrite the description and usage note from the cells and axes now covered (after merging)."""
        count = len(self.cell_ids)
        sliced = f", sliced by {' and '.join(self.axes)}" if self.axes else ""
        self.description = (
            f"Migrated from the legacy report '{self.filename}' ({_cells_text(self.cell_ids)}). "
            f"{describe(self.expr)}{sliced}. Proven by recomputation on the raw data."
        )
        if self.axes:
            self.notes = [f"Put {' and '.join(self.axes)} on the visual (rows / columns) and this one measure gives all {count} numbers."]
        elif count > 1:
            self.notes = [f"{count} numbers in the report use exactly this formula."]
        else:
            self.notes = []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "dax": self.dax,
            "formula": describe(self.expr),
            "cells": self.cell_ids,
            "notes": self.notes,
            "display_folder": self.display_folder,
        }


@dataclass
class MigrationPlan:
    table: str
    measures: list[MigratedMeasure] = field(default_factory=list)
    not_writable: list[dict] = field(default_factory=list)  # reproduced cells that cannot become measures, and why

    def get(self, measure_id: str) -> Optional[MigratedMeasure]:
        return next((m for m in self.measures if m.id == measure_id), None)

    def to_dict(self) -> dict:
        return {"table": self.table, "measures": [m.to_dict() for m in self.measures], "not_writable": self.not_writable}


# --- naming -------------------------------------------------------------------------------


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


def _short(expr: Expr) -> str:
    """A readable base name for what a formula measures."""
    if isinstance(expr, Measure):
        column = expr.column or "rows"
        return {
            Op.SUM: f"Total {column}",
            Op.AVERAGE: f"Average {column}",
            Op.MIN: f"Lowest {column}",
            Op.MAX: f"Highest {column}",
            Op.DISTINCT_COUNT: f"Distinct {column}",
            Op.COUNT: f"Count of {column}" if expr.column else "Row count",
        }[expr.op]
    if isinstance(expr, Ratio):
        return f"{_short(expr.numerator)} per {_short(expr.denominator)}"
    return f"{_short(expr.minuend)} less {_short(expr.subtrahend)}"


_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"


def _is_period(label: str) -> bool:
    """A year, quarter or month heading: a slice of time, not the name of what is measured."""
    return bool(re.fullmatch(rf"(?:fy)?\s*\d{{4}}|q[1-4](?:\s+\d{{4}})?|{_MONTH}\.?(?:[\s-]+\d{{2,4}})?|\d{{1,2}}[-/]\d{{2,4}}", label.strip().casefold()))


def _shared_heading(results: list[CellResult]) -> Optional[str]:
    """The column heading every cell of a group sits under, when it names the measure (not a period)."""
    headings = {r.target.col_labels[-1] for r in results if r.target.col_labels}
    if len(headings) == 1 and len(results) == sum(1 for r in results if r.target.col_labels):
        heading = headings.pop()
        if heading and not _is_period(heading):
            return heading
    return None


def _filter_words(result: CellResult) -> list[str]:
    """The filter values of a cell, in the order its labels mention them (so "West - 2024", as in the report)."""
    labels = [label.casefold() for label in (*result.target.row_labels, *result.target.col_labels, *result.target.context_labels)]
    values: list[str] = []
    for flt in filters_of(result.expr):
        for value in flt.value if isinstance(flt.value, tuple) else (flt.value,):
            text = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
            if text not in values:
                values.append(text)

    def position(text: str) -> int:
        return next((i for i, label in enumerate(labels) if text.casefold() in label), len(labels))

    return sorted(values, key=position)


class _Namer:
    def __init__(self, taken: set[str]) -> None:
        self.taken = {t.casefold() for t in taken}

    def release(self, name: str) -> None:
        self.taken.discard(name.casefold())

    def claim(self, name: str) -> str:
        name = re.sub(r"\s+", " ", name).strip()[:MAX_NAME_LENGTH].rstrip(" -")
        candidate, n = name, 1
        while candidate.casefold() in self.taken:
            n += 1
            candidate = f"{name} ({n})"
        self.taken.add(candidate.casefold())
        return candidate


# --- grouping -----------------------------------------------------------------------------


def _key(flt: Filter) -> tuple:
    return (flt.column, flt.part)


def _same_scope(expr: Expr) -> bool:
    """True when every measure inside a formula carries the same filters (so dropping some drops them everywhere)."""
    measures: list[Measure] = []

    def walk(node: Expr) -> None:
        if isinstance(node, Measure):
            measures.append(node)
        elif isinstance(node, Ratio):
            walk(node.numerator)
            walk(node.denominator)
        else:
            walk(node.minuend)
            walk(node.subtrahend)

    walk(expr)
    first = canonical_filters(measures[0].filters)
    return all(canonical_filters(m.filters) == first for m in measures)


def _without(expr: Expr, keys: set[tuple]) -> Expr:
    def strip(node: Expr) -> Expr:
        if isinstance(node, Measure):
            return Measure(node.op, node.column, canonical_filters(tuple(f for f in node.filters if _key(f) not in keys)), node.group)
        if isinstance(node, Ratio):
            return Ratio(strip(node.numerator), strip(node.denominator), node.scale)
        return Difference(strip(node.minuend), strip(node.subtrahend))

    return strip(expr)


def _canonical(expr: Expr) -> Expr:
    if isinstance(expr, Measure):
        return Measure(expr.op, expr.column, canonical_filters(expr.filters), expr.group)
    if isinstance(expr, Ratio):
        return Ratio(_canonical(expr.numerator), _canonical(expr.denominator), expr.scale)
    return Difference(_canonical(expr.minuend), _canonical(expr.subtrahend))


def _axis_name(flt: Filter) -> str:
    return f"{flt.part.value.capitalize()} of {flt.column}" if flt.part else flt.column


def build_plan(
    report_id: str,
    table: str,
    filename: str,
    results: list[CellResult],
    evaluate: Callable[[Expr], Optional[float]],
    existing_names: Optional[set[str]] = None,
    columns: Optional[list[str]] = None,
) -> MigrationPlan:
    """Group and name the measures for every cell proven on the raw data.

    ``evaluate`` computes a formula on the same raw rows (for the grouped measure's own check);
    ``existing_names`` and ``columns`` keep names from colliding with the model's measures or columns.
    """
    plan = MigrationPlan(table)
    for result in results:
        if result.status == "REPRODUCED" and not result.writable:
            plan.not_writable.append(
                {"cell": result.target.id, "reason": "it only matches the cleaned data, not the table in the model"}
            )
    writable = [r for r in results if r.writable]
    namer = _Namer({*(existing_names or set()), *(columns or [])})
    dax = DaxCompiler(table)

    by_shape: dict[str, list[CellResult]] = {}
    for result in writable:
        by_shape.setdefault(result.shape or describe(result.expr), []).append(result)

    for group in by_shape.values():
        # cells with literally the same formula share one measure
        by_formula: dict[Expr, list[CellResult]] = {}
        for result in group:
            by_formula.setdefault(_canonical(result.expr), []).append(result)
        varying = _varying_keys(list(by_formula))
        if len(by_formula) >= 2 and varying and all(_same_scope(r.expr) for r in group):
            _add(plan, _grouped(report_id, table, filename, group, varying, namer, dax, evaluate), namer)
        else:
            for expr, members in by_formula.items():
                _add(plan, _single(report_id, filename, expr, members, namer), namer)
    return plan


def _add(plan: MigrationPlan, measure: MigratedMeasure, namer: _Namer) -> None:
    """Add a measure, unless one with exactly the same DAX exists: then it simply covers these cells too."""
    same = next((m for m in plan.measures if m.dax == measure.dax), None)
    if same is None:
        plan.measures.append(measure)
        return
    namer.release(measure.name)
    same.cell_ids.extend(measure.cell_ids)
    same.checks.extend(c for c in measure.checks if c.cell_id is not None)
    for axis in measure.axes:
        if axis not in same.axes:
            same.axes.append(axis)
    if same.axes:
        same.kind = "grouped"
    same.refresh()


def _varying_keys(exprs: list[Expr]) -> set[tuple]:
    values: dict[tuple, set[str]] = {}
    for expr in exprs:
        for flt in filters_of(expr):
            values.setdefault(_key(flt), set()).add(repr(flt.value))
    return {k for k, v in values.items() if len(v) > 1}


def _cells_text(refs: list[str]) -> str:
    return refs[0] if len(refs) == 1 else f"{refs[0]} to {refs[-1]} ({len(refs)} cells)"


def _single(report_id: str, filename: str, expr: Expr, members: list[CellResult], namer: _Namer) -> MigratedMeasure:
    first = members[0]
    heading = _shared_heading(members) if len(members) > 1 else None
    base = heading or _short(expr)
    words = _filter_words(first)
    name = namer.claim(" - ".join([base, *words]) if words else base)
    measure = MigratedMeasure(
        id=f"{report_id}:{_slug(name)}",
        name=name,
        kind="single",
        expr=expr,
        dax=first.dax,
        description="",
        cell_ids=[m.target.id for m in members],
        checks=[MeasureCheck(describe(expr), first.dax, first.recomputed, first.target.id)],
        filename=filename,
    )
    measure.refresh()
    return measure


def _grouped(report_id, table, filename, group, varying, namer, dax: DaxCompiler, evaluate) -> MigratedMeasure:
    template = group[0].expr
    base = _without(template, varying)
    heading = _shared_heading(group)
    name = namer.claim(heading or _short(base))
    body = dax.compile(base)
    axes: list[str] = []
    for flt in sorted(filters_of(template), key=lambda f: (f.part is not None, f.column)):  # categories before dates
        if _key(flt) in varying and _axis_name(flt) not in axes:
            axes.append(_axis_name(flt))
    checks = []
    base_value = evaluate(base)
    if base_value is not None:
        checks.append(MeasureCheck("the measure itself, with nothing filtered", body, base_value))
    for result in group:
        checks.append(MeasureCheck(", ".join(_filter_words(result)) or describe(result.expr), result.dax, result.recomputed, result.target.id))
    measure = MigratedMeasure(
        id=f"{report_id}:{_slug(name)}",
        name=name,
        kind="grouped",
        expr=base,
        dax=body,
        description="",
        cell_ids=[r.target.id for r in group],
        checks=checks,
        axes=axes,
        filename=filename,
    )
    measure.refresh()
    return measure
