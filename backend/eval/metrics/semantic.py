"""Semantic-type and domain accuracy, and calibration of the confidences that go with them."""

from __future__ import annotations

from typing import Any

from eval.common import Dataset, expected_calibration_error


def column_rows(ds: Dataset, result: Any) -> list[dict]:
    """One row per labelled column: what it is, what PowerPilot said, how sure it was."""
    predicted = {c.name: c for c in result.dataset_profile.columns}
    rows = []
    for name, truth in ds.columns.items():
        column = predicted.get(name)
        rows.append(
            {
                "dataset": ds.id,
                "column": name,
                "truth": truth,
                "predicted": str(column.semantic_type) if column else "missing",
                "confidence": float(column.confidence) if column else 0.0,
            }
        )
    return rows


def score_columns(rows: list[dict]) -> dict:
    """Accuracy over every column, and precision/recall for the columns that mean something (not `unknown`)."""
    n = len(rows)
    correct = [r["truth"] == r["predicted"] for r in rows]
    truths = [r for r in rows if r["truth"] != "unknown"]
    claims = [r for r in rows if r["predicted"] not in ("unknown", "missing")]
    hits = sum(r["truth"] == r["predicted"] for r in truths)
    precise = sum(r["truth"] == r["predicted"] for r in claims)
    recall = hits / len(truths) if truths else None
    precision = precise / len(claims) if claims else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else (0.0 if truths and claims else None)
    return {
        "columns": n,
        "accuracy": sum(correct) / n if n else None,
        "labelled_columns": len(truths),
        "recall_labelled": recall,
        "claims": len(claims),
        "precision_claims": precision,
        "f1_labelled": f1,
        "ece": expected_calibration_error([r["confidence"] for r in rows], correct),
    }


def domain_row(ds: Dataset, result: Any) -> dict:
    profile = result.dataset_profile
    predicted = str(profile.detected_domain)
    return {
        "dataset": ds.id,
        "truth": ds.domain,
        "predicted": predicted,
        "confidence": float(profile.domain_confidence),
        "correct": predicted == ds.domain,
        "label_confidence": ds.domain_label_confidence,
    }
