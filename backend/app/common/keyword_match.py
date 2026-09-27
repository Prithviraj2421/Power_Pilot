"""Whole-token keyword matching for column names.

Every entity detector and domain classifier decides what a column means partly
by checking whether a short keyword appears in its name -- e.g. does "emp"
appear in this column, suggesting EMPLOYEE. Sixteen of those plugins did this
with a raw Python `in` check, which matches *inside* other words:

    "emp" in "temperature_c"   -> True   (t-EMP-erature)
    "rep" in "report_date"     -> True   (REP-ort_date)
    "id"  in "paid_amount"     -> True   (pa-ID-_amount)
    "city" in "capacity"       -> True   (capa-CITY)
    "fee" in "feedback_score"  -> True   (FEE-dback_score)
    "time" in "overtime_hours" -> True   (over-TIME-_hours)

Each of those is a real column name from a real dataset, and each one got
mistagged -- which is how a synthetic weather-station dataset (temperature,
humidity, pressure, battery -- nothing about people) classified as HR at 0.667
confidence: `temperature_c` alone was enough to satisfy the "found an EMPLOYEE
column" check.

This module replaces the raw `in` check with one that treats a keyword as
matched only when it appears as a complete token, not a fragment glued to
other letters. Digits and underscores count as separators, which matters for
snake_case column names: "emp_id" still matches "emp" (letters directly
bounded by "_"), while "temperature_c" does not (the "emp" inside it is
bounded by letters on both sides).
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable


@lru_cache(maxsize=512)
def _compiled(keyword: str) -> re.Pattern[str]:
    """A cached pattern for one keyword: matched only between non-letters.

    Lookaround on *letters specifically* (not the regex `\\w` class, which
    would treat underscore as part of the word and break the "emp_id" case
    above) is what lets "emp" match "emp_id" but not "temperature_c".
    """
    escaped = re.escape(keyword.lower())
    return re.compile(rf"(?<![a-zA-Z]){escaped}(?![a-zA-Z])")


def contains_keyword(text: str, keyword: str) -> bool:
    """Whether ``keyword`` appears in ``text`` as a whole token.

    Case-insensitive. Both snake_case boundaries (``emp_id``) and plain
    concatenation inside another word (``temperature``) are handled correctly;
    see the module docstring for worked examples.
    """
    return _compiled(keyword).search(text.lower()) is not None


def matched_keywords(text: str, keywords: Iterable[str]) -> set[str]:
    """The subset of ``keywords`` that appear in ``text`` as whole tokens."""
    lowered = text.lower()
    return {kw for kw in keywords if _compiled(kw).search(lowered) is not None}


def count_keyword_matches(text: str, keywords: Iterable[str]) -> int:
    """How many of ``keywords`` appear in ``text`` as whole tokens."""
    return len(matched_keywords(text, keywords))


def any_keyword_matches(text: str, keywords: Iterable[str]) -> bool:
    """Whether any of ``keywords`` appears in ``text`` as a whole token."""
    lowered = text.lower()
    return any(_compiled(kw).search(lowered) is not None for kw in keywords)
