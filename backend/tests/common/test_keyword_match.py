"""Tests for whole-token keyword matching.

Every case here is a real column name that was misclassified before this module
existed, traced from an actual bug: a synthetic weather-station dataset
(temperature, humidity, pressure, battery -- nothing about people) classified
as HR at 0.667 confidence, because `"emp" in "temperature_c"` is True in plain
Python (t-EMP-erature).
"""

from __future__ import annotations

import pytest

from app.common.keyword_match import (
    any_keyword_matches,
    contains_keyword,
    count_keyword_matches,
    matched_keywords,
)


# ---------------------------------------------------------------------------
# False positives that raw `in` produces and must be rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("column_name", "keyword"),
    [
        ("temperature_c", "emp"),  # t-EMP-erature -- the bug that started this
        ("report_date", "rep"),
        ("prepared_by", "rep"),
        ("paid_amount", "id"),
        ("valid_flag", "id"),
        ("provider_name", "id"),
        ("guide_version", "id"),
        ("capacity", "city"),
        ("felicity_score", "city"),
        ("feedback_score", "fee"),
        ("coffee_break_minutes", "fee"),
        ("overtime_hours", "time"),
        ("lifetime_value", "time"),
        ("announce_date", "no"),
        ("normal_range", "no"),
        ("statement_date", "state"),
    ],
)
def test_keyword_glued_inside_another_word_is_not_a_match(
    column_name: str, keyword: str
) -> None:
    assert contains_keyword(column_name, keyword) is False


# ---------------------------------------------------------------------------
# Genuine matches must still work, including snake_case abbreviations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("column_name", "keyword"),
    [
        ("emp_id", "emp"),  # underscore-delimited abbreviation
        ("emp_name", "emp"),
        ("employee_id", "employee"),
        ("sales_rep", "rep"),
        ("rep_name", "rep"),
        ("employee_id", "id"),
        ("customer_id", "id"),
        ("id", "id"),
        ("city", "city"),
        ("delivery_city", "city"),
        ("city_code", "city"),
        ("late_fee", "fee"),
        ("fee_amount", "fee"),
        ("order_time", "time"),
        ("time_of_day", "time"),
        ("invoice_no", "no"),
        ("hire_date", "hire_date"),  # multi-word keyword as one token
        ("employee_hire_date", "hire_date"),
    ],
)
def test_keyword_as_a_whole_token_is_a_match(column_name: str, keyword: str) -> None:
    assert contains_keyword(column_name, keyword) is True


def test_matching_is_case_insensitive() -> None:
    assert contains_keyword("Employee_ID", "id") is True
    assert contains_keyword("TEMPERATURE_C", "emp") is False


# ---------------------------------------------------------------------------
# Set-returning and counting helpers
# ---------------------------------------------------------------------------


def test_matched_keywords_returns_only_real_hits() -> None:
    result = matched_keywords("temperature_c", {"emp", "temp", "cel"})
    assert "emp" not in result


def test_count_keyword_matches_ignores_glued_substrings() -> None:
    keywords = {"emp", "staff", "manager", "rep", "worker"}
    assert count_keyword_matches("temperature_c", keywords) == 0
    assert count_keyword_matches("staff_manager_rep", keywords) == 3


def test_any_keyword_matches_short_circuits_correctly() -> None:
    assert any_keyword_matches("temperature_c", {"emp", "rep", "id"}) is False
    assert any_keyword_matches("employee_id", {"emp", "rep", "id"}) is True


def test_a_keyword_that_is_the_entire_text_matches() -> None:
    assert contains_keyword("id", "id") is True
    assert contains_keyword("time", "time") is True
