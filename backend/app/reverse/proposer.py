"""An optional language model that *proposes* formulas; computation alone decides which are believed.

The model sees only the shape of the problem: column names (with a coarse type), the report's header
labels for one number, and its unit. It never sees a data value. What it returns is parsed through a
whitelist into the same IR the rest of the system uses; every candidate is then recomputed by
``verify()`` and accepted only if it lands on the number the report shows. A wrong, invented or
malformed suggestion costs nothing: it simply fails that check.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional, Protocol

import pandas as pd

from app.core.config import Settings, get_settings
from app.intelligence.kpi.ir import Compare, DatePart, Difference, Expr, Filter, Measure, Op, Ratio
from app.reverse.models import TargetCell

MAX_CANDIDATES = 10

SYSTEM_PROMPT = """You help reverse-engineer how a number in a legacy business report was calculated.
You are given the column names of the underlying data table (with a coarse type for each), the labels
printed around ONE number in the report, and the number's unit. You are NOT given the data or the number.
Propose up to 10 candidate formulas, most likely first, as JSON only: a list of objects.

A candidate is one of:
  {"op": "sum|average|min|max|count|distinct_count", "column": "<column or null for count of rows>",
   "filters": [{"column": "<column>", "compare": "==|!=|>|>=|<|<=", "value": <string or number>,
                "part": null|"year"|"quarter"|"month"}]}
  {"ratio": {"numerator": <measure>, "denominator": <measure>, "scale": 1 or 100}}
  {"difference": {"minuend": <measure>, "subtrahend": <measure>}}
Use only the column names given. Filter values must come from the report labels. "part" applies a
year/quarter/month to a date column (then value is a whole number). Output the JSON list and nothing else."""


class Proposer(Protocol):
    def propose(self, table: str, df: pd.DataFrame, target: TargetCell) -> list[Expr]:
        """Candidate formulas for ``target``. They are only candidates; the caller proves them."""
        ...


def column_roles(df: pd.DataFrame) -> list[dict[str, str]]:
    """Name and coarse type of each column. No values."""
    roles = []
    for name in df.columns:
        series = df[name]
        if pd.api.types.is_datetime64_any_dtype(series):
            kind = "date"
        elif pd.api.types.is_bool_dtype(series):
            kind = "flag"
        elif pd.api.types.is_numeric_dtype(series):
            kind = "number"
        else:
            kind = "text"
        roles.append({"name": str(name), "type": kind})
    return roles


def build_prompt(table: str, df: pd.DataFrame, target: TargetCell) -> str:
    """The user message: column names and the labels around one number, never data."""
    payload = {
        "table": table,
        "columns": column_roles(df),
        "row_labels": list(target.row_labels),
        "column_labels": list(target.col_labels),
        "title_labels": list(target.context_labels),
        "row_headings": list(target.row_axis_names),
        "unit": target.unit,
    }
    return json.dumps(payload, ensure_ascii=False)


# --- turning the reply into IR, through a whitelist ---------------------------------------


def _measure(spec: Any, columns: set[str]) -> Optional[Measure]:
    if not isinstance(spec, dict):
        return None
    try:
        op = Op(str(spec.get("op")))
    except ValueError:
        return None
    if op is Op.RATIO:
        return None
    column = spec.get("column")
    if column is not None and column not in columns:
        return None
    filters: list[Filter] = []
    for raw in spec.get("filters") or []:
        flt = _filter(raw, columns)
        if flt is None:
            return None
        filters.append(flt)
    try:
        return Measure(op, column, tuple(filters))
    except ValueError:
        return None


def _filter(raw: Any, columns: set[str]) -> Optional[Filter]:
    if not isinstance(raw, dict) or raw.get("column") not in columns:
        return None
    try:
        compare = Compare(str(raw.get("compare", "==")))
        part = DatePart(raw["part"]) if raw.get("part") else None
        value = raw.get("value")
        if isinstance(value, list):
            value = tuple(value)
        if compare is Compare.IN and not isinstance(value, tuple):
            return None
        return Filter(raw["column"], compare, value, part)
    except (ValueError, TypeError, KeyError):
        return None


def parse_candidates(text: str, columns: list[str]) -> list[Expr]:
    """Candidate expressions from a model reply. Anything unknown or malformed is silently dropped."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    known = set(columns)
    out: list[Expr] = []
    for item in items[:MAX_CANDIDATES] if isinstance(items, list) else []:
        expr: Optional[Expr] = None
        if isinstance(item, dict) and "ratio" in item and isinstance(item["ratio"], dict):
            top, bottom = _measure(item["ratio"].get("numerator"), known), _measure(item["ratio"].get("denominator"), known)
            scale = item["ratio"].get("scale", 1)
            if top and bottom and scale in (1, 100):
                expr = Ratio(top, bottom, float(scale))
        elif isinstance(item, dict) and "difference" in item and isinstance(item["difference"], dict):
            first, second = _measure(item["difference"].get("minuend"), known), _measure(item["difference"].get("subtrahend"), known)
            if first and second:
                expr = Difference(first, second)
        else:
            expr = _measure(item, known)
        if expr is not None:
            out.append(expr)
    return out


class AnthropicProposer:
    """Asks Claude for candidate formulas for one number at a time."""

    def __init__(self, settings: Optional[Settings] = None, client: Optional[Any] = None) -> None:
        self._settings = get_settings() if settings is None else settings
        self._client = client

    def _get_client(self) -> Optional[Any]:
        if self._client is None:
            from app.intelligence.llm.llm_copilot import make_anthropic_client

            self._client = make_anthropic_client(self._settings)
        return self._client

    def propose(self, table: str, df: pd.DataFrame, target: TargetCell) -> list[Expr]:
        client = self._get_client()
        if client is None:
            return []
        response = client.messages.create(
            model=self._settings.llm_model,
            max_tokens=2000,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": build_prompt(table, df, target)}],
        )
        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        return parse_candidates(text, [str(c) for c in df.columns])


def default_proposer(settings: Optional[Settings] = None) -> Optional[Proposer]:
    """The language-model proposer when a key is configured; None otherwise (the search runs alone)."""
    settings = get_settings() if settings is None else settings
    return AnthropicProposer(settings) if settings.llm_enabled else None
