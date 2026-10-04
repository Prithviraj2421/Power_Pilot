"""KPI validity (do the references exist and does it execute?), value accuracy, and coverage of hand-computed truth.

Every emitted KPI's DAX is executed by an *independent* evaluator (tests/kpi/dax_oracle.py, which parses the DAX text and
shares no code with the pandas compiler) over the frame the model would hold, so "the number shown" is checked against "what
the exported formula computes", not against itself.
"""

from __future__ import annotations

import math
from typing import Any, Optional

import pandas as pd

from app.common.powerbi_names import dax_references
from app.intelligence.kpi.column_resolver import table_for
from eval.common import Dataset, close
from tests.kpi.dax_oracle import evaluate_dax

COUNTROWS = "COUNTROWS("


def _rows(frame: pd.DataFrame, columns: list[str]) -> list[dict]:
    subset = frame[columns] if columns else frame.iloc[:, :1]
    return subset.astype(object).where(subset.notna(), None).to_dict("records")


def execute(dax: str, table: str, frame: pd.DataFrame) -> tuple[bool, Optional[float], str]:
    """(references exist, value, problem) for one DAX measure body."""
    refs = dax_references(dax)
    if any(t != table for t, _ in refs):
        return False, None, "refers to another table"
    missing = [c for _, c in refs if c not in frame.columns]
    if missing:
        return False, None, f"missing column(s) {missing}"
    try:
        value = evaluate_dax(dax, _rows(frame, sorted({c for _, c in refs})))
    except Exception as exc:
        return True, None, f"does not execute: {exc}"
    if value is None or not math.isfinite(value):
        return True, None, "evaluates to BLANK or a non-finite number"
    return True, float(value), ""


def kpi_rows(ds: Dataset, run: Any) -> tuple[list[dict], dict]:
    """Per-KPI rows and the dataset-level scores."""
    result, cleaned = run.result, run.cleaned
    table = table_for(result.dataset_profile)
    rows = []
    for kpi in result.kpi_report.all_kpis:
        if not kpi.formula:
            rows.append({"dataset": ds.id, "kpi": kpi.name, "refs_exist": False, "executes": False, "value_matches": False, "oracle_value": None, "reported": kpi.computed_value, "problem": "no formula"})
            continue
        refs_ok, value, problem = execute(kpi.formula, table, cleaned)
        rows.append(
            {
                "dataset": ds.id,
                "kpi": kpi.name,
                "refs_exist": refs_ok,
                "executes": value is not None,
                "value_matches": value is not None and close(kpi.computed_value, value, 1e-6),
                "oracle_value": value,
                "reported": kpi.computed_value,
                "problem": problem,
            }
        )
    truth_hits = []
    for truth in ds.kpis:
        found = any(r["executes"] and close(r["oracle_value"], truth["value"], 1e-4) for r in rows)
        truth_hits.append({"dataset": ds.id, "truth_kpi": truth["name"], "found": found, "value": truth["value"]})
    n = len(rows)
    scores = {
        "emitted": n,
        "validity_rate": sum(r["executes"] for r in rows) / n if n else None,
        "value_accuracy": sum(r["value_matches"] for r in rows) / n if n else None,
        "truth_kpis": len(ds.kpis),
        "truth_coverage": sum(t["found"] for t in truth_hits) / len(truth_hits) if truth_hits else None,
    }
    return rows + [], {**scores, "_truth": truth_hits}
