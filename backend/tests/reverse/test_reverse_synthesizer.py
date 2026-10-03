"""The formula search: what it finds, what it refuses to claim, and how it stays bounded."""

from __future__ import annotations

import time

import pandas as pd
import pytest

from app.intelligence.kpi.compilers import PandasCompiler
from app.intelligence.kpi.ir import Compare, DatePart, Difference, Filter, Measure, Op, Ratio
from app.reverse.describe import describe, shape_of
from app.reverse.index import DataIndex
from app.reverse.synthesizer import Synthesizer, significant_digits, tolerance_for

from tests.reverse.conftest import target

PC = PandasCompiler()
WEST_2024 = (Filter("Region", Compare.EQ, "West"), Filter("Order Date", Compare.EQ, 2024, DatePart.YEAR))


def test_a_money_figure_is_explained_by_exactly_one_formula(golden_synth, golden_df) -> None:
    value = PC.evaluate(Measure(Op.SUM, "Sales", WEST_2024), golden_df)
    search = golden_synth.search(target(round(value, 2), ["West"], ["2024"]))
    shapes = {c.shape for c in search.candidates}
    # Order Date and Ship Date years give the same number for West, but they are the only two ways
    assert len(search.candidates) == 2
    assert all(c.expr.op is Op.SUM and c.expr.column == "Sales" for c in search.candidates)
    assert shapes == {
        "sum(Sales)[Region==*,year(Order Date)==*]",
        "sum(Sales)[Region==*,year(Ship Date)==*]",
    }


def test_every_regional_total_matches_exactly_one_measure_across_all_filters(golden_synth, golden_df) -> None:
    for region, rows in golden_df.groupby("Region"):
        search = golden_synth.search(target(round(rows["Sales"].sum(), 2), [region]))
        assert [describe(c.expr) for c in search.candidates] == [f"Sum of Sales where Region is {region}"]


def test_matching_is_at_the_precision_the_report_shows(golden_synth, golden_df) -> None:
    exact = golden_df[golden_df["Region"] == "West"]["Sales"].sum()
    in_thousands = target(round(exact / 1000) * 1000.0, ["West"], scale=1000.0, decimals=0, shown=f"{exact / 1000:.0f}K")
    assert in_thousands.tolerance == 500.0
    assert golden_synth.search(in_thousands).candidates[0].expr == Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, "West"),))

    off_by_a_thousand = target(round(exact, 2) + 1000, ["West"])
    assert golden_synth.search(off_by_a_thousand).candidates == []  # a different number is not "close enough"


def test_a_number_that_is_one_digit_out_is_not_matched(golden_synth, golden_df) -> None:
    exact = round(golden_df[golden_df["Region"] == "West"]["Sales"].sum(), 2)
    assert golden_synth.search(target(exact, ["West"])).candidates
    assert not golden_synth.search(target(exact + 0.1, ["West"])).candidates


def test_small_counts_fit_several_formulas_and_are_all_reported(golden_synth) -> None:
    search = golden_synth.search(target(9, ["Home Office"], ["Customers"], decimals=0, shown="9"))
    described = [describe(c.expr) for c in search.candidates]
    assert "Number of different Customer ID where Segment is Home Office" in described
    assert search.candidates[0].expr.column == "Customer ID"  # the heading's word ranks it first ...
    assert len(search.candidates) >= 2  # ... but a small number can fit other columns by chance, and says so


def test_the_headings_word_ranks_the_candidates(golden_synth, golden_df) -> None:
    segment = golden_df[golden_df["Segment"] == "Corporate"]
    value = float(segment["Customer ID"].nunique())
    for word, column in (("Customers", "Customer ID"), ("Products", "Product ID"), ("Cities", "City")):
        value = float(segment[column].nunique())
        search = golden_synth.search(target(value, ["Corporate"], [word], decimals=0, shown=f"{value:.0f}"))
        assert search.candidates[0].expr.column == column, (word, [describe(c.expr) for c in search.candidates])


def test_labels_are_dropped_one_at_a_time_when_using_them_all_finds_nothing(golden_synth, golden_df) -> None:
    # "West" and "2023" name filters, but the figure is West's all-years total.
    value = round(golden_df[golden_df["Region"] == "West"]["Sales"].sum(), 2)
    search = golden_synth.search(target(value, ["West"], ["2023"]))
    best = search.candidates[0]
    assert best.expr == Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, "West"),))
    assert best.dropped == ("2023",) and "label '2023' was not used as a filter" in best.reasons


def test_when_nothing_is_dropped_nothing_is_reported_as_dropped(golden_synth, golden_df) -> None:
    value = PC.evaluate(Measure(Op.SUM, "Sales", WEST_2024), golden_df)
    best = golden_synth.search(target(round(value, 2), ["West"], ["2024"])).candidates[0]
    assert best.dropped == () and best.used == ("West", "2024")


def test_a_percent_is_a_ratio_of_two_measures(golden_synth, golden_df) -> None:
    furniture = golden_df[golden_df["Category"] == "Furniture"]
    margin = furniture["Profit"].sum() / furniture["Sales"].sum()
    search = golden_synth.search(target(round(margin, 3), ["Furniture"], ["Profit margin"], unit="percent", scale=0.01, decimals=1))
    best = search.candidates[0]
    scope = (Filter("Category", Compare.EQ, "Furniture"),)
    assert best.expr == Ratio(Measure(Op.SUM, "Profit", scope), Measure(Op.SUM, "Sales", scope))


def test_a_share_of_total_divides_by_the_unfiltered_total(golden_synth, golden_df) -> None:
    share = golden_df[golden_df["Region"] == "West"]["Sales"].sum() / golden_df["Sales"].sum()
    search = golden_synth.search(target(round(share, 3), ["West"], ["Share of sales"], unit="percent", scale=0.01, decimals=1))
    best = search.candidates[0]
    assert isinstance(best.expr, Ratio)
    assert best.expr.numerator == Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, "West"),))
    assert best.expr.denominator == Measure(Op.SUM, "Sales", ())


def test_a_plain_number_with_a_percent_heading_can_be_a_ratio_times_100(golden_synth, golden_df) -> None:
    furniture = golden_df[golden_df["Category"] == "Furniture"]
    margin = 100 * furniture["Profit"].sum() / furniture["Sales"].sum()
    search = golden_synth.search(target(round(margin, 2), ["Furniture"], ["Margin %"], decimals=2))
    assert any(isinstance(c.expr, Ratio) and c.expr.scale == 100.0 for c in search.candidates)


def test_a_difference_is_tried_when_the_words_hint_at_one(golden_synth, golden_df) -> None:
    value = round(golden_df["Sales"].sum() - golden_df["Profit"].sum(), 2)
    search = golden_synth.search(target(value, [], ["Net cost"], decimals=2))
    assert any(isinstance(c.expr, Difference) for c in search.candidates)


def test_ratios_and_differences_are_only_a_fallback_for_precise_numbers(golden_synth, golden_df) -> None:
    """With a 1-digit number, some ratio or difference always fits by chance; claiming one would be a lie."""
    search = golden_synth.search(target(7, ["Nowhere"], ["Mystery"], decimals=0, shown="7"))
    assert significant_digits(search.target) == 1
    assert not any(isinstance(c.expr, (Ratio, Difference)) for c in search.candidates)


def test_a_figure_no_formula_explains_gets_no_candidates(golden_synth) -> None:
    search = golden_synth.search(target(123456.789, ["West"], ["2024"], decimals=3))
    assert search.candidates == [] and not search.exhausted


def test_the_time_budget_stops_the_search_and_says_so(golden_synth, golden_df) -> None:
    value = round(golden_df["Sales"].sum() + 1, 2)
    search = golden_synth.search(target(value, ["West", "Consumer"], ["2023", "Technology"]), deadline=time.monotonic() - 1)
    assert search.exhausted and search.tried == 0


def test_the_number_of_filter_sets_tried_is_bounded(golden_index, golden_df) -> None:
    bounded = Synthesizer(golden_index, max_filter_sets=3)
    value = round(golden_df["Sales"].sum() + 7, 2)
    search = bounded.search(target(value, ["West", "Consumer", "Technology"], ["2023", "First Class"]))
    assert search.tried <= 3 * 2  # per pass (normal, then fallback)


def test_candidates_are_one_per_shape_best_first(golden_synth) -> None:
    search = golden_synth.search(target(9, ["Home Office"], ["Customers"], decimals=0, shown="9"))
    shapes = [c.shape for c in search.candidates]
    assert len(shapes) == len(set(shapes))
    scores = [c.score for c in search.candidates]
    assert scores == sorted(scores, reverse=True)


def test_significant_digits_and_tolerance() -> None:
    assert significant_digits(target(32368.41, shown="32,368.41")) == 7
    assert significant_digits(target(0.103, shown="10.3%", unit="percent", decimals=1, scale=0.01)) == 3
    assert significant_digits(target(1_200_000, shown="1.2M", decimals=1, scale=1e6)) == 2
    assert significant_digits(target(0, shown="0")) == 1
    assert tolerance_for(target(100.0, decimals=0)) > 0.5


def test_blank_results_never_match() -> None:
    frame = pd.DataFrame({"Region": ["A", "B"], "Sales": [None, 5.5]})
    synth = Synthesizer(DataIndex(frame))
    search = synth.search(target(0.0, ["A"], decimals=0))
    assert all(c.value == 0.0 for c in search.candidates)
    assert not any(isinstance(c.expr, Measure) and c.expr.op is Op.SUM and c.expr.column == "Sales" for c in search.candidates)


def test_shapes_abstract_the_filter_values() -> None:
    a = Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, "West"), Filter("Order Date", Compare.EQ, 2024, DatePart.YEAR)))
    b = Measure(Op.SUM, "Sales", (Filter("Order Date", Compare.EQ, 2023, DatePart.YEAR), Filter("Region", Compare.EQ, "East")))
    assert shape_of(a) == shape_of(b) == "sum(Sales)[Region==*,year(Order Date)==*]"
    assert shape_of(a) != shape_of(Measure(Op.AVERAGE, "Sales", a.filters))
