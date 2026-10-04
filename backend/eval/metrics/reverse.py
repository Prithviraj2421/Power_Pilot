"""Reverse-engineering: how many correct numbers are reproduced with the right formula, and are planted mistakes found?

* reproduced (correct formula): a correct, non-derived cell reported REPRODUCED *with the formula that really produced it*
* false alarm: a correct cell reported NOT_REPRODUCIBLE
* detected: a planted mistake reported NOT_REPRODUCIBLE;  precision = detected / (detected + false alarms),  recall = detected / planted
  (a planted mistake that comes back REPRODUCED is a miss; AMBIGUOUS is neither detected nor a false alarm)
* hint ok: the plain-English hint on a detected mistake names the right kind of problem
"""

from __future__ import annotations

import time
from typing import Any, Optional

from app.intelligence.kpi.ir import Difference, Expr, Measure, Ratio
from app.reverse.describe import canonical_filters
from app.reverse.engine import ReverseEngine
from app.reverse.models import AMBIGUOUS, DERIVED, NOT_REPRODUCIBLE, REPRODUCED
from app.reverse.report_reader import read_report
from eval.common import Dataset
from eval.reports.generate import ReportSpec

HINT_WORDS = {
    "swapped-digits": ("swapped", "one digit differs"),
    "one-row": ("row", "order", "customer", "left out"),
    "missing-category": ("left out", "missing"),
}


def normalise(expr: Expr) -> Expr:
    if isinstance(expr, Measure):
        return Measure(expr.op, expr.column, canonical_filters(expr.filters), expr.group)
    if isinstance(expr, Ratio):
        return Ratio(normalise(expr.numerator), normalise(expr.denominator), expr.scale)
    if isinstance(expr, Difference):
        return Difference(normalise(expr.minuend), normalise(expr.subtrahend))
    return expr


def run_report(ds: Dataset, spec: ReportSpec, content: bytes, filename: str, **engine_kwargs: Any) -> tuple[list[dict], dict]:
    started = time.perf_counter()
    parsed = read_report(content, filename)
    report = ReverseEngine(ds.frame, "Data", time_budget=60.0, **engine_kwargs).run(parsed, filename, "eval")
    seconds = time.perf_counter() - started
    by_cell = {(r.target.row_labels[-1] if r.target.row_labels else "", r.target.col_labels[-1] if r.target.col_labels else ""): r for r in report.results}

    rows = []
    for cell in spec.cells:
        result = by_cell.get((cell.row, cell.col))
        status = result.status if result else "MISSING"
        correct_formula = bool(
            result and cell.expected is not None and result.status == REPRODUCED and result.expr is not None
            and normalise(result.expr) == normalise(cell.expected)
        )
        hint = (result.hint or "").lower() if result else ""
        rows.append(
            {
                "dataset": ds.id, "report": spec.name, "table": cell.table, "row": cell.row, "col": cell.col,
                "kind": "mistake" if cell.mistake else ("derived" if cell.formula else "correct"),
                "mistake": cell.mistake or "", "status": status, "correct_formula": correct_formula,
                "hint_ok": bool(cell.mistake and any(w in hint for w in HINT_WORDS[cell.mistake])),
            }
        )
    correct = [r for r in rows if r["kind"] == "correct"]
    planted = [r for r in rows if r["kind"] == "mistake"]
    detected = sum(r["status"] == NOT_REPRODUCIBLE for r in planted)
    false_alarms = sum(r["status"] == NOT_REPRODUCIBLE for r in correct)
    summary = {
        "dataset": ds.id, "report": spec.name, "kind": spec.kind, "seconds": seconds,
        "correct_cells": len(correct),
        "reproduced_correct_formula": sum(r["correct_formula"] for r in correct),
        "reproduced_any": sum(r["status"] == REPRODUCED for r in correct),
        "ambiguous": sum(r["status"] == AMBIGUOUS for r in correct),
        "false_alarms": false_alarms,
        "planted": len(planted), "detected": detected,
        "hints_ok": sum(r["hint_ok"] for r in planted if r["status"] == NOT_REPRODUCIBLE),
        "derived_ok": sum(1 for r in rows if r["kind"] == "derived" and r["status"] == DERIVED),
        "derived": sum(1 for r in rows if r["kind"] == "derived"),
    }
    return rows, summary


def ratio(a: float, b: float) -> Optional[float]:
    return a / b if b else None
