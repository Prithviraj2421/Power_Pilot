"""The baseline: a model given the CSV head and a question, with no pipeline behind it.

It is asked the same things PowerPilot is measured on: the dataset's domain, each column's semantic type, a few KPIs with
their values for the *whole* dataset, and the fixed copilot questions. It can only see the first rows, which is exactly the
situation of someone pasting a file into a chat.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.core.config import get_settings
from eval.common import Dataset
from eval.llm import CachedLLM

HEAD_ROWS = 15
TYPES = "customer, product, revenue, profit, cost, quantity, date, region, employee, identifier, unknown"
DOMAINS = "retail, finance, hr, healthcare, marketing, logistics, unknown"
SYSTEM = "You are a careful data analyst. Answer exactly in the requested format and nothing else."


def head_csv(ds: Dataset) -> str:
    return ds.frame.head(HEAD_ROWS).to_csv(index=False)


def _ask(llm: CachedLLM, prompt: str, max_tokens: int = 2000) -> str:
    response = llm.messages.create(
        model=get_settings().llm_model,
        max_tokens=max_tokens,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in response.content if getattr(b, "type", None) == "text")


def _json(text: str) -> Optional[Any]:
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def classify(llm: CachedLLM, ds: Dataset) -> dict:
    """{"domain": str, "domain_confidence": float, "columns": {name: {"type": str, "confidence": float}}}"""
    prompt = (
        f"Here are the first {HEAD_ROWS} rows of a CSV file.\n\n{head_csv(ds)}\n"
        f'Reply with JSON only: {{"domain": one of [{DOMAINS}], "domain_confidence": 0-1, '
        f'"columns": {{<column name>: {{"type": one of [{TYPES}], "confidence": 0-1}}}} }} covering every column.'
    )
    return _json(_ask(llm, prompt)) or {}


def kpis(llm: CachedLLM, ds: Dataset) -> list[dict]:
    """[{"name": str, "value": float}] for the WHOLE dataset, from the head alone."""
    prompt = (
        f"Here are the first {HEAD_ROWS} rows of a CSV file with {len(ds.frame)} rows in total.\n\n{head_csv(ds)}\n"
        "List the 5 most useful KPIs for this data and your best value for each over ALL rows. "
        'Reply with JSON only: [{"name": str, "value": number}].'
    )
    parsed = _json(_ask(llm, prompt))
    return parsed if isinstance(parsed, list) else []


def answer(llm: CachedLLM, ds: Dataset, question: str) -> str:
    prompt = (
        f"Here are the first {HEAD_ROWS} rows of a CSV file with {len(ds.frame)} rows in total.\n\n{head_csv(ds)}\n"
        f"Question about the WHOLE file: {question}\nAnswer in one or two sentences."
    )
    return _ask(llm, prompt, 600)
