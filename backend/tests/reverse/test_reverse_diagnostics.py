"""Hints for numbers nothing reproduces: they explain the difference, and never decide a match."""

from __future__ import annotations

import pandas as pd
import pytest

from app.intelligence.kpi.ir import Compare, Filter, Measure, Op
from app.reverse.diagnostics import difference_text, digit_hint, diagnose, scale_hint, show_value
from app.reverse.index import DataIndex

from tests.reverse.conftest import target


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Region": ["North", "North", "South", "South", "East"],
            "Order ID": ["o1", "o1", "o2", "o3", "o1"],  # o1 spans North and East
            "Sales": [100.50, 200.25, 50.75, 300.00, 10.50],
            "Customer ID": ["c1", "c2", "c3", "c4", "c5"],
        }
    )


@pytest.fixture(scope="module")
def index(frame) -> DataIndex:
    return DataIndex(frame)


TOTAL = Measure(Op.SUM, "Sales")  # 662.00
COUNT_ORDERS = Measure(Op.DISTINCT_COUNT, "Order ID")  # 3


def report(value: float, **kw):
    return target(value, ["Total"], ["Sales"], axis=["Region"], **kw)


def test_swapped_digits_are_named_with_both_numbers() -> None:
    cell = report(1234.56)
    text = digit_hint(1234.56, 1243.56, cell)
    assert "swapped" in text and "1,243.56" in text and "1,234.56" in text


def test_a_single_wrong_digit_is_a_typing_mistake() -> None:
    text = digit_hint(1234.56, 1284.56, report(1234.56))
    assert "one digit differs" in text and "typing" in text


def test_digits_that_differ_in_many_places_are_not_called_a_typo() -> None:
    assert digit_hint(1234.56, 9876.54, report(1234.56)) is None
    assert digit_hint(1234.56, 1234.56, report(1234.56)) is None  # identical
    assert digit_hint(1234.56, 12345.6, report(1234.56)) is None  # different length


@pytest.mark.parametrize("factor", [10, 100, 1000, 1_000_000])
def test_a_units_slip_is_named(factor) -> None:
    cell = report(662.0 * factor, decimals=0)
    assert f"{factor:,.0f} times" in scale_hint(662.0 * factor, 662.0, cell)
    assert f"1/{factor:,.0f} of" in scale_hint(662.0 / factor, 662.0, report(662.0 / factor))


def test_an_unrelated_ratio_is_not_a_units_slip() -> None:
    assert scale_hint(700.0, 662.0, report(700.0)) is None
    assert scale_hint(0.0, 662.0, report(0.0)) is None


def test_a_count_off_by_one_or_two(index) -> None:
    text = diagnose(report(4.0, decimals=0, shown="4"), 3.0, COUNT_ORDERS, index)
    assert text.startswith("Off by 1") and "the data gives 3" in text
    assert "Off by 2" in diagnose(report(5.0, decimals=0, shown="5"), 3.0, COUNT_ORDERS, index)


def test_one_row_left_out(index) -> None:
    text = diagnose(report(662.0 - 50.75), 662.0, TOTAL, index)
    assert "lower than the data by 50.75" in text and "exactly one row's Sales" in text and "Order ID o2" in text
    assert "left out of the report" in text


def test_one_row_counted_twice(index) -> None:
    text = diagnose(report(662.0 + 10.5), 662.0, TOTAL, index)
    assert "higher than the data by 10.50" in text and "counted in the report by mistake" in text and "Order ID o1" in text


def test_a_whole_order_left_out_when_no_single_row_fits(index) -> None:
    text = diagnose(report(662.0 - 311.25), 662.0, TOTAL, index)  # o1 = 100.50 + 200.25 + 10.50
    assert "exactly the Sales of one Order ID (o1, 3 row(s))" in text


def test_two_rows_together(index) -> None:
    text = diagnose(report(662.0 - 310.5), 662.0, TOTAL, index)  # 300.00 + 10.50
    assert "two rows' Sales together" in text


def test_a_whole_category_left_out_is_preferred_when_the_heading_names_it(index) -> None:
    text = diagnose(report(662.0 - 350.75), 662.0, TOTAL, index)  # South = 50.75 + 300.00
    assert "every row where Region is South left out" in text and "may be missing from the report" in text


def test_a_category_not_named_by_any_heading_is_only_a_last_resort(frame) -> None:
    # Customer ID c3 alone is one row (50.75): the more natural reading ("one row") must win over "customer c3 left out".
    index = DataIndex(frame)
    text = diagnose(target(662.0 - 50.75, ["Total"], ["Sales"]), 662.0, TOTAL, index)
    assert "exactly one row's Sales" in text and "Customer ID c3 left out" not in text


def test_a_filtered_formula_keeps_its_filters_when_explaining(index) -> None:
    north = Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, "North"),))  # 300.75
    text = diagnose(report(300.75 - 100.50), 300.75, north, index)
    assert "exactly one row's Sales" in text and "Region is North" in text  # the rule is spelled out


def test_with_no_explanation_the_hint_still_states_the_difference(index) -> None:
    text = diagnose(report(700.0), 662.0, TOTAL, index)
    assert "shows 700.00 but the same rule gives 662.00" in text and "+38.00" in text and "Rule: Sum of Sales" in text


def test_percent_differences_are_in_percentage_points() -> None:
    cell = target(0.125, unit="percent", scale=0.01, decimals=1)
    text = difference_text(0.125, 0.103, cell)
    assert "12.5%" in text and "10.3%" in text and "+2.2 percentage points" in text


def test_numbers_are_shown_the_way_the_report_prints_them() -> None:
    assert show_value(0.125, target(0.125, unit="percent", scale=0.01, decimals=1)) == "12.5%"
    assert show_value(1234.5, target(1234.5, decimals=2)) == "1,234.50"
    assert show_value(1_200_000, target(1_200_000, scale=1e6, decimals=1)) == "1,200,000"


def test_a_hint_is_text_only_never_a_match(index) -> None:
    result = diagnose(report(662.0 - 50.75), 662.0, TOTAL, index)
    assert isinstance(result, str)  # diagnostics return words; the engine alone decides statuses
