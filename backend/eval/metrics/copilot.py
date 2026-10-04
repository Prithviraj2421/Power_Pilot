"""Copilot grounding: how often does an answer state a number the data does not support?

A fixed, dataset-generic question set (counts, totals, averages, extremes, "which group is highest") is asked of each system.
The truth for every question is computed by hand-written pandas. An answer's numbers are then checked against the **universe
of facts that are true of the dataset**: row and column counts, per-column missing and distinct counts, and per numeric column the count, sum, mean, min, max, median, standard
deviation, plus per-group counts, sums and means for categorical columns. A number outside that universe (at the precision it
is written) is *unsupported*. Small whole numbers (10 or fewer, as in "top 3") are ignored.

`correct` is separate: the answer states the one number that answers the question (and the right group, when asked which).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.reverse.numbers import ParsedNumber, parse_number
from eval.common import Dataset

_NUMBER = re.compile(r"[-(]?[$€£₹]?\d[\d,]*(?:\.\d+)?\s?(?:%|[KkMmBb](?![a-zA-Z]))?\)?")
MAX_GROUPS = 20


@dataclass(frozen=True)
class Question:
    text: str
    truth: float  # the number that answers it
    group: Optional[str] = None  # for "which group" questions: the right group


def _numeric_columns(ds: Dataset) -> list[str]:
    out = []
    for column, kind in ds.columns.items():
        s = ds.frame[column]
        if kind in ("identifier", "date") or not pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s):
            continue
        if s.nunique() >= 10:
            out.append(column)
    return out


def _category_columns(ds: Dataset) -> list[str]:
    frame = ds.frame
    return [
        c for c in frame.columns
        if (pd.api.types.is_string_dtype(frame[c]) or frame[c].dtype == object) and 2 <= frame[c].nunique() <= MAX_GROUPS
    ]


def questions(ds: Dataset) -> list[Question]:
    frame, numbers, categories = ds.frame, _numeric_columns(ds), _category_columns(ds)
    out = [Question("How many rows are in the dataset?", float(len(frame)))]
    for column in numbers[:2]:
        out.append(Question(f"What is the total of {column}?", float(frame[column].sum())))
        out.append(Question(f"What is the average {column}?", float(frame[column].mean())))
    if numbers:
        out.append(Question(f"What is the highest {numbers[0]}?", float(frame[numbers[0]].max())))
    if numbers and categories:
        totals = frame.groupby(categories[0])[numbers[0]].sum()
        out.append(Question(f"Which {categories[0]} has the highest total {numbers[0]}?", float(totals.max()), str(totals.idxmax())))
    return out


def fact_universe(ds: Dataset) -> list[float]:
    frame = ds.frame
    facts: list[float] = [float(len(frame)), float(len(frame.columns))]
    for column in frame.columns:  # facts about the table itself: missing values and distinct values per column
        facts += [float(frame[column].isna().sum()), float(frame[column].nunique())]
    numbers = _numeric_columns(ds)
    for column in numbers:
        s = frame[column].dropna()
        facts += [float(s.count()), float(s.sum()), float(s.mean()), float(s.min()), float(s.max()), float(s.median()), float(s.std() or 0), float(s.nunique())]
    for category in _category_columns(ds):
        facts += [float(v) for v in frame[category].value_counts().tolist()]
        for column in numbers[:6]:
            grouped = frame.groupby(category)[column]
            facts += [float(v) for v in grouped.sum().tolist()] + [float(v) for v in grouped.mean().tolist()]
    return facts


def numbers_in(text: str) -> list[ParsedNumber]:
    found = []
    for match in _NUMBER.finditer(text):
        parsed = parse_number(match.group(0).strip())
        if parsed is not None:
            found.append(parsed)
    return found


def _supported(number: ParsedNumber, universe: list[float]) -> bool:
    """True when some true fact rounds to the number as written."""
    slack = max(number.tolerance, 1e-9)
    # an answer may also give a fraction as a percent (0.15 -> "15%") or a percent as a number
    options = [number.value] + ([number.value * 100, number.value / 100] if number.unit == "percent" else [])
    return any(abs(value - fact) <= slack * (100 if value != number.value else 1) for value in options for fact in universe)


def grade(ds: Dataset, question: Question, answer: str, universe: list[float]) -> dict:
    asked = [n.value for n in numbers_in(question.text)]
    stated = numbers_in(answer)
    unsupported = [
        n.value
        for n in stated
        if not (float(n.value).is_integer() and abs(n.value) <= 10 and n.unit == "number")
        and not _supported(n, universe + asked)
    ]
    correct = any(abs(n.value - question.truth) <= max(n.tolerance, 1e-9) + 1e-9 * abs(question.truth) for n in stated)
    if question.group and question.group.lower() not in answer.lower():
        correct = False
    return {
        "dataset": ds.id,
        "question": question.text,
        "answered": bool(stated),
        "correct": correct,
        "unsupported_numbers": len(unsupported),
        "has_unsupported": bool(unsupported),
        "answer": answer.replace("\n", " ")[:300],
    }


def pipeline_facts(result) -> list[float]:
    """Numbers the pipeline itself computed and handed to the copilot (its fact sheet). A pipeline system may cite these too."""
    from app.intelligence.llm.grounding import build_fact_sheet

    return [n.value for n in numbers_in(build_fact_sheet(result))]
