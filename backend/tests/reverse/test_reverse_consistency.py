"""Neighbours settle what one number cannot, and show what a mistaken number should have been."""

from __future__ import annotations

import pandas as pd
import pytest

from app.intelligence.kpi.compilers import PandasCompiler
from app.intelligence.kpi.ir import Compare, DatePart, Filter, Measure, Op
from app.reverse import consistency
from app.reverse.describe import describe
from app.reverse.index import DataIndex
from app.reverse.synthesizer import Synthesizer

from tests.reverse.conftest import target

PC = PandasCompiler()


def customers(df, segment: str, column: str = "Customer ID") -> float:
    return float(df[df["Segment"] == segment][column].nunique())


def customer_cells(df) -> list:
    return [
        target(customers(df, s), [s], ["Customers"], decimals=0, shown=f"{customers(df, s):.0f}", ident=f"S!B{i}")
        for i, s in enumerate(["Consumer", "Corporate", "Home Office"], start=2)
    ]


def test_one_small_number_fitting_two_columns_is_ambiguous_on_its_own(golden_synth, golden_df) -> None:
    (cell,) = [c for c in customer_cells(golden_df) if c.row_labels == ("Corporate",)]
    resolution = consistency.resolve([golden_synth.search(cell)])[cell.id]
    assert resolution.ambiguous and resolution.chosen is not None
    assert {describe(c.expr) for c in [resolution.chosen, *resolution.alternatives]} >= {
        "Number of different Customer ID where Segment is Corporate",
        "Number of different Customer Name where Segment is Corporate",
    }


def test_the_column_that_explains_every_neighbour_wins(golden_synth, golden_df) -> None:
    searches = [golden_synth.search(c) for c in customer_cells(golden_df)]
    resolutions = consistency.resolve(searches)
    for cell in customer_cells(golden_df):
        resolution = resolutions[cell.id]
        assert not resolution.ambiguous
        assert resolution.chosen.expr.column == "Customer ID"
    corporate = resolutions["S!B3"]
    assert any("also explains" in reason for reason in corporate.reasons)
    assert corporate.support >= 2


def test_neighbours_that_explain_two_formulas_equally_leave_the_cell_ambiguous(golden_synth) -> None:
    frame = pd.DataFrame(
        {
            "Segment": ["Aa", "Aa", "Bb", "Bb", "Cc"],
            "Customer ID": ["a1", "a2", "b1", "b2", "c1"],
            "Customer Name": ["x1", "x2", "y1", "y2", "z1"],  # identical counts in every group
            "Amount": [1.5, 2.5, 3.5, 4.5, 5.5],
        }
    )
    synth = Synthesizer(DataIndex(frame))
    cells = [target(n, [s], ["Customers"], decimals=0, shown=str(int(n)), ident=f"S!B{i}") for i, (s, n) in enumerate([("Aa", 2), ("Bb", 2), ("Cc", 1)], 2)]
    resolutions = consistency.resolve([synth.search(c) for c in cells])
    assert all(r.ambiguous for r in resolutions.values())


def test_a_cell_that_breaks_its_columns_pattern_is_called_out() -> None:
    frame = pd.DataFrame(
        {
            "Region": [n for n in ("Alpha", "Beta", "Gamma", "Delta", "Omega") for _ in (0, 1)],
            "Sales": [10.5, 11.25, 20.5, 21.25, 30.5, 31.25, 40.5, 41.25, 50.5, 51.25],
            "Units": [101.5, 7.25, 3.5, 1.75, 6.5, 1.25, 4.5, 8.25, 9.5, 17.25],
        }
    )
    synth = Synthesizer(DataIndex(frame))
    sales = frame.groupby("Region")["Sales"].sum()
    cells = [target(sales[r], [r], ["Value"], ident=f"S!B{i}") for i, r in enumerate(["Alpha", "Beta", "Gamma", "Delta"], 2)]
    odd = frame[frame["Region"] == "Omega"]["Units"].sum()
    cells.append(target(odd, ["Omega"], ["Value"], ident="S!B6"))
    resolutions = consistency.resolve([synth.search(c) for c in cells])
    assert resolutions["S!B6"].chosen.expr.column == "Units"
    assert any("neighbours" in note for note in resolutions["S!B6"].notes)
    assert not resolutions["S!B2"].notes


def test_pattern_breaks_are_not_flagged_in_small_groups() -> None:
    frame = pd.DataFrame({"Region": ["Alpha", "Alpha", "Beta", "Beta"], "Sales": [10.5, 11.25, 20.5, 21.25], "Units": [7.5, 1.25, 3.5, 1.75]})
    synth = Synthesizer(DataIndex(frame))
    cells = [target(21.75, ["Alpha"], ["Value"], ident="S!B2"), target(41.75, ["Beta"], ["Value"], ident="S!B3"), target(8.75, ["Alpha"], ["Other"], ident="S!C2")]
    resolutions = consistency.resolve([synth.search(c) for c in cells])
    assert all(not r.notes for r in resolutions.values())


# --- the expected formula for a number nothing explains -----------------------------------


def region_year_cells(df, replace: dict | None = None) -> list:
    cells = []
    for i, region in enumerate(["Central", "East", "South", "West"], start=3):
        for j, year in enumerate([2023, 2024]):
            expr = Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, region), Filter("Order Date", Compare.EQ, year, DatePart.YEAR)))
            value = round(PC.evaluate(expr, df), 2)
            value = (replace or {}).get((region, year), value)
            cells.append(target(value, [region], [str(year)], ident=f"S!{'BC'[j]}{i}", axis=["Region"]))
    return cells


def prepare(synth, df, extra=(), replace=None):
    cells = [*region_year_cells(df, replace), *extra]
    searches = {c.id: synth.search(c) for c in cells}
    resolutions = consistency.resolve(list(searches.values()))
    groups = consistency.groups(list(searches.values()))
    return cells, searches, resolutions, groups


def test_the_expectation_for_a_mistaken_cell_is_what_its_neighbours_rule_gives(golden_synth, golden_df) -> None:
    cells, searches, resolutions, groups = prepare(golden_synth, golden_df, replace={("East", 2024): 16097.19})
    bad = next(c for c in cells if c.row_labels == ("East",) and c.col_labels == ("2024",))
    assert resolutions[bad.id].chosen is None
    expectation = consistency.expectation_for(bad.id, golden_synth, golden_df, searches, resolutions, groups)
    assert expectation.value == pytest.approx(16079.19)
    assert describe(expectation.expr) == "Sum of Sales where the year of Order Date is 2024 and Region is East"
    assert "same heading" in expectation.source or "same row" in expectation.source


def test_a_cell_with_no_region_label_gets_an_all_regions_expectation(golden_synth, golden_df) -> None:
    all_regions = target(71258.44, ["All Regions"], ["2024"], ident="S!C7", axis=["Region"])
    cells, searches, resolutions, groups = prepare(golden_synth, golden_df, extra=[all_regions])
    expectation = consistency.expectation_for("S!C7", golden_synth, golden_df, searches, resolutions, groups)
    assert expectation.value == pytest.approx(103626.85)
    assert describe(expectation.expr) == "Sum of Sales where the year of Order Date is 2024"  # varying Region dropped


def test_a_filter_all_the_neighbours_share_is_kept(golden_synth, golden_df) -> None:
    """The year is stated once in a title; the cell's own labels never repeat it."""
    cells = []
    for i, region in enumerate(["Central", "East", "South", "West"], start=3):
        expr = Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, region), Filter("Order Date", Compare.EQ, 2024, DatePart.YEAR)))
        cells.append(target(round(PC.evaluate(expr, golden_df), 2), [region], ["Sales"], ctx=["2024"], ident=f"S!B{i}"))
    stray = target(1.0, ["East"], ["Sales"], ident="S!B9")  # a number without the title's year
    searches = {c.id: golden_synth.search(c) for c in [*cells, stray]}
    resolutions = consistency.resolve(list(searches.values()))
    groups = consistency.groups(list(searches.values()))
    expectation = consistency.expectation_for("S!B9", golden_synth, golden_df, searches, resolutions, groups)
    assert "year of Order Date is 2024" in describe(expectation.expr) and "Region is East" in describe(expectation.expr)


def test_no_pattern_means_no_expectation(golden_synth, golden_df) -> None:
    lonely = target(123456.0, ["West"], ["2024"], ident="S!B2")
    searches = {lonely.id: golden_synth.search(lonely)}
    resolutions = consistency.resolve(list(searches.values()))
    assert consistency.expectation_for(lonely.id, golden_synth, golden_df, searches, resolutions, consistency.groups(list(searches.values()))) is None


def test_ambiguous_peers_do_not_define_a_pattern(golden_synth, golden_df) -> None:
    frame = pd.DataFrame({"Segment": ["Aa", "Aa", "Bb", "Bb"], "ID": ["a1", "a2", "b1", "b2"], "Name": ["x1", "x2", "y1", "y2"], "Amount": [1.5, 2.5, 3.5, 4.5]})
    synth = Synthesizer(DataIndex(frame))
    cells = [target(2, ["Aa"], ["Customers"], decimals=0, shown="2", ident="S!B2"), target(2, ["Bb"], ["Customers"], decimals=0, shown="2", ident="S!B3"), target(9, ["Cc"], ["Customers"], decimals=0, shown="9", ident="S!B4")]
    searches = {c.id: synth.search(c) for c in cells}
    resolutions = consistency.resolve(list(searches.values()))
    assert consistency.pattern_for("S!B4", searches, resolutions, *consistency.groups(list(searches.values()))) is None
