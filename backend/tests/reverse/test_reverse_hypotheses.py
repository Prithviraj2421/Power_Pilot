"""What a report's words say about its formulas: filters named by labels, and hints about the measure."""

from __future__ import annotations

import pandas as pd
import pytest

from app.intelligence.kpi.ir import Compare, DatePart, Filter, Op
from app.reverse.hypotheses import LabelReader, affinity, stem
from app.reverse.index import DataIndex, normalise

from tests.reverse.conftest import target


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Order Date": ["19/03/2024", "05/07/2024", "28/01/2025", "02/11/2025"],
            "Ship Date": ["22/03/2024", "09/07/2024", "30/01/2025", "05/11/2025"],
            "Region": ["West", "East", "West", "South"],
            "Segment": ["Home Office", "Consumer", "Corporate", "Home Office"],
            "Year": [2024, 2024, 2025, 2025],
            "Customer ID": ["a", "b", "c", "d"],
            "Sales": [10.5, 20.5, 30.5, 40.5],
            "Postal Code": [1, 2, 3, 4],
        }
    )


@pytest.fixture(scope="module")
def reader(df) -> LabelReader:
    return LabelReader(DataIndex(df))


def only(hint):
    assert len(hint.options) == 1, hint
    return hint.options[0].filters


def test_column_roles_are_found(df) -> None:
    index = DataIndex(df)
    assert index.date_columns == ["Order Date", "Ship Date"]
    assert index.measure_columns == ["Sales"]
    assert "Postal Code" in index.distinct_columns and "Postal Code" not in index.measure_columns  # a label, never summed
    assert index.calendar_columns == ["Year"] and "Year" not in index.measure_columns
    assert index.date_years["Order Date"] == (2024, 2025)


def test_a_label_naming_a_value_becomes_an_equality_filter(reader) -> None:
    assert only(reader.read("West", ())) == (Filter("Region", Compare.EQ, "West"),)
    assert only(reader.read("  west  ", ())) == (Filter("Region", Compare.EQ, "West"),)  # case and spacing do not matter


def test_multi_word_values_match_as_a_whole_not_word_by_word(reader) -> None:
    assert only(reader.read("Home Office", ())) == (Filter("Segment", Compare.EQ, "Home Office"),)
    assert reader.read("Home", ()).options == ()
    assert reader.read("Office", ()).options == ()


def test_a_value_inside_a_longer_label_is_found_on_whole_tokens(reader) -> None:
    assert only(reader.read("West Region", ())) == (Filter("Region", Compare.EQ, "West"),)
    assert only(reader.read("Sales - Home Office", ())) == (Filter("Segment", Compare.EQ, "Home Office"),)
    assert reader.read("Western", ()).options == ()  # "west" inside another word is not a match


def test_words_that_mean_a_total_never_name_a_value(reader) -> None:
    for label in ("Total", "All", "Grand Total", "Overall", "Average"):
        assert reader.read(label, ()).options == ()


def test_a_year_is_a_date_part_on_every_date_column_and_a_value_of_a_year_column(reader) -> None:
    hint = reader.read("2024", ())
    filters = {f for option in hint.options for f in option.filters}
    assert filters == {
        Filter("Order Date", Compare.EQ, 2024, DatePart.YEAR),
        Filter("Ship Date", Compare.EQ, 2024, DatePart.YEAR),
        Filter("Year", Compare.EQ, 2024),
    }
    assert all(len(option.filters) == 1 for option in hint.options)  # alternatives, never combined


def test_years_outside_the_data_name_nothing(reader) -> None:
    assert reader.read("1999", ()).options == ()
    assert reader.read("2031", ()).options == ()


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("FY2025", [Filter("Order Date", Compare.EQ, 2025, DatePart.YEAR)]),
        ("Q3", [Filter("Order Date", Compare.EQ, 3, DatePart.QUARTER)]),
        ("Q1 2025", [Filter("Order Date", Compare.EQ, 2025, DatePart.YEAR), Filter("Order Date", Compare.EQ, 1, DatePart.QUARTER)]),
        ("Jan", [Filter("Order Date", Compare.EQ, 1, DatePart.MONTH)]),
        ("January 2025", [Filter("Order Date", Compare.EQ, 2025, DatePart.YEAR), Filter("Order Date", Compare.EQ, 1, DatePart.MONTH)]),
        ("Mar-24", [Filter("Order Date", Compare.EQ, 2024, DatePart.YEAR), Filter("Order Date", Compare.EQ, 3, DatePart.MONTH)]),
        ("2024-07", [Filter("Order Date", Compare.EQ, 2024, DatePart.YEAR), Filter("Order Date", Compare.EQ, 7, DatePart.MONTH)]),
        ("11/2025", [Filter("Order Date", Compare.EQ, 2025, DatePart.YEAR), Filter("Order Date", Compare.EQ, 11, DatePart.MONTH)]),
    ],
)
def test_calendar_labels(reader, label, expected) -> None:
    options = [o for o in reader.read(label, ()).options if o.filters[0].column == "Order Date"]
    assert len(options) == 1
    assert sorted(options[0].filters, key=repr) == sorted(expected, key=repr)


def test_the_heading_decides_which_column_a_value_belongs_to() -> None:
    frame = pd.DataFrame({"City": ["West", "Paris"], "Region": ["West", "East"], "Sales": [1.5, 2.5]})
    reader = LabelReader(DataIndex(frame))
    options = reader.read("West", ("Region",)).options
    assert len(options) == 2  # both columns have a "West"
    best = max(options, key=lambda o: o.affinity)
    assert best.filters == (Filter("Region", Compare.EQ, "West"),) and best.affinity == 1.0


def test_labels_become_hints_for_a_whole_cell(reader) -> None:
    hints = reader.hints_for(target(1.0, rows=["West"], cols=["Average Sales 2024"], ctx=["Orders by Region"], axis=["Region"]))
    assert [h.label for h in hints.slots] == ["West", "Average Sales 2024"]
    assert Op.AVERAGE in hints.ops and not hints.ratio and not hints.percent
    assert hints.column_affinity("Sales") == 1.0 and hints.column_affinity("Customer ID") == 0.0


@pytest.mark.parametrize(
    ("labels", "ops", "ratio", "percent", "difference"),
    [
        (["Total Sales"], {Op.SUM}, False, False, False),
        (["Customers"], {Op.DISTINCT_COUNT, Op.COUNT}, False, False, False),
        (["Number of Orders"], {Op.DISTINCT_COUNT, Op.COUNT}, False, False, False),
        (["Highest price"], {Op.MAX}, False, False, False),
        (["Lowest price"], {Op.MIN}, False, False, False),
        (["Profit margin"], set(), True, False, False),
        (["Share of sales"], set(), True, False, False),
        (["Growth %"], set(), True, True, False),
        (["Net revenue"], set(), False, False, True),
    ],
)
def test_measure_hints(reader, labels, ops, ratio, percent, difference) -> None:
    hints = reader.hints_for(target(1.0, cols=labels))
    assert (hints.ops, hints.ratio, hints.percent, hints.difference) == (ops, ratio, percent, difference)


def test_a_percent_cell_always_hints_at_a_ratio(reader) -> None:
    hints = reader.hints_for(target(0.12, unit="percent", scale=0.01, cols=["Anything"]))
    assert hints.percent and hints.ratio


def test_column_affinity_uses_the_distinctive_words_of_a_column_name() -> None:
    assert affinity(["Customers"], "Customer ID") == 1.0  # "id" is generic; "customer" is what counts
    assert affinity(["Customers"], "Customer Name") == 1.0
    assert affinity(["Product Sales"], "Product Name") == 1.0
    assert affinity(["Sales"], "Sub-Category") == 0.0
    assert affinity(["Sales by region"], "Order Date") == 0.0
    assert affinity(["Ship"], "Ship Mode") == 0.5


def test_helpers() -> None:
    assert [stem(w) for w in ("Sales", "customers", "Categories", "glass", "us")] == ["sale", "customer", "category", "glass", "us"]
    assert normalise("  Phones & Accessories ") == "phones accessories"
