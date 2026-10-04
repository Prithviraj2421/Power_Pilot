"""Shared pieces of the benchmark: where things live, loading a dataset with its labels, and small statistics."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

import pandas as pd

EVAL = Path(__file__).resolve().parent
RAW = EVAL / "datasets" / "raw"
LABELS = EVAL / "labels"
REPORTS = EVAL / "reports"
RESULTS = EVAL / "results"
CACHE = EVAL / "cache"
SEED = 20240601  # every random choice in the benchmark derives from this


@dataclass(frozen=True)
class Dataset:
    id: str
    title: str
    domain: str  # true domain label
    domain_label_confidence: str
    columns: dict[str, str]  # true semantic type of every column
    kpis: list[dict]  # {"name", "value"} computed by hand-written pandas on the raw file
    frame: pd.DataFrame

    @property
    def name(self) -> str:
        return f"{self.id}.csv"


def dataset_ids() -> list[str]:
    return sorted(p.stem for p in LABELS.glob("*.json"))


def load(ident: str) -> Dataset:
    label = json.loads((LABELS / f"{ident}.json").read_text(encoding="utf-8"))
    frame = pd.read_csv(RAW / f"{ident}.csv", low_memory=False)
    return Dataset(
        id=ident,
        title=label["title"],
        domain=label["domain"],
        domain_label_confidence=label.get("domain_label_confidence", "high"),
        columns=label["columns"],
        kpis=label["kpis"],
        frame=frame,
    )


def expected_calibration_error(confidences: Sequence[float], correct: Sequence[bool], bins: int = 10) -> Optional[float]:
    """ECE: the bin-weighted gap between how confident predictions were and how often they were right."""
    n = len(confidences)
    if n == 0:
        return None
    total = 0.0
    for b in range(bins):
        low, high = b / bins, (b + 1) / bins
        members = [i for i, c in enumerate(confidences) if (low <= c < high) or (b == bins - 1 and c == 1.0)]
        if not members:
            continue
        accuracy = sum(correct[i] for i in members) / len(members)
        confidence = sum(confidences[i] for i in members) / len(members)
        total += len(members) / n * abs(accuracy - confidence)
    return total


def close(a: Optional[float], b: Optional[float], rel: float = 1e-6) -> bool:
    if a is None or b is None or not (math.isfinite(a) and math.isfinite(b)):
        return False
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


def mean(values: Iterable[float]) -> Optional[float]:
    values = [v for v in values if v is not None and math.isfinite(v)]
    return sum(values) / len(values) if values else None
