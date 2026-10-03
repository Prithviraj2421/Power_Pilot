"""The engine's judgement: what is proven, what is derived, what is only a hint, and what is refused."""

from __future__ import annotations

import pandas as pd
import pytest

from app.intelligence.kpi.ir import Compare, Filter, Measure, Op
from app.reverse import consistency
from app.reverse.engine import ReverseEngine
from app.reverse.models import AMBIGUOUS, DERIVED, NOT_REPRODUCIBLE, REPRODUCED, DerivedInfo, ParsedReport
from app.reverse.synthesizer import Candidate, Synthesizer
from app.reverse.index import DataIndex
from app.reverse.describe import shape_of

from tests.reverse.conftest import target


@pytest.fixture(scope="module")
def orders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Region": ["North", "North", "South", "South", "East"],
            "Sales": [100.50, 200.25, 50.75, 300.00, 10.50],
            "Units": [1, 2, 3, 4, 5],
        }
    )


def run(frame, targets, **kwargs):
    return ReverseEngine(frame, "Orders", **kwargs).run(ParsedReport(targets=list(targets)), "r.xlsx", "rid")


def by_id(report):
    return {r.target.id: r for r in report.results}


def cell(value, region, ident, **kw):
    return target(value, [region], ["Sales"], ident=ident, **kw)


# --- derived ------------------------------------------------------------------------------


def total(value, sources, op="sum", ident="S!B9", kind="total_label", formula=None):
    return target(value, ["Total"], ["Sales"], ident=ident, derived=DerivedInfo(kind, tuple(sources), op, formula))


def test_a_total_that_adds_up_is_derived_with_the_arithmetic(orders) -> None:
    parts = [cell(300.75, "North", "S!B2"), cell(350.75, "South", "S!B3"), cell(10.5, "East", "S!B4")]
    report = run(orders, [*parts, total(662.0, ["S!B2", "S!B3", "S!B4"])])
    result = by_id(report)["S!B9"]
    assert result.status == DERIVED and result.derived_check.consistent and not result.writable
    assert result.formula == "Sum of the 3 numbers it totals" and "Adding up the 3 numbers" in result.derived_check.explanation
    assert result.derived_check.matches_data is None or result.derived_check.matches_data


def test_rounding_in_the_parts_is_allowed_for(orders) -> None:
    parts = [target(10.4, [n], ["V"], decimals=0, shown="10", ident=f"S!B{i}") for i, n in enumerate(["a1", "b1", "c1"], 2)]
    # shown parts are 10 + 10 + 10 = 30, the total shows 31: within the rounding of three numbers shown to 0 decimals
    t = target(31.0, ["Total"], ["V"], decimals=0, shown="31", ident="S!B9", derived=DerivedInfo("total_label", ("S!B2", "S!B3", "S!B4"), "sum"))
    assert ReverseEngine._check_derived(t, {p.id: p for p in parts}).consistent
    far = target(34.0, ["Total"], ["V"], decimals=0, shown="34", ident="S!B9", derived=t.derived)
    assert not ReverseEngine._check_derived(far, {p.id: p for p in parts}).consistent


@pytest.mark.parametrize(
    ("op", "value", "ok"),
    [("sum", 30.0, True), ("average", 10.0, True), ("min", 5.0, True), ("max", 15.0, True), ("sum", 31.0, False), ("average", 11.0, False)],
)
def test_each_aggregate_is_checked(op, value, ok) -> None:
    values = {"S!B2": 5.0, "S!B3": 10.0, "S!B4": 15.0}
    parts = {k: target(v, [k], ["V"], decimals=1, ident=k) for k, v in values.items()}
    t = target(value, ["Total"], ["V"], decimals=1, ident="S!B9", derived=DerivedInfo("total_label", tuple(values), op))
    check = ReverseEngine._check_derived(t, parts)
    assert check.consistent is ok
    if not ok:
        assert "not what its own parts give" in check.explanation


def test_a_formula_that_is_not_an_aggregate_is_not_recomputed() -> None:
    t = target(62.0, ["Twice"], ["V"], ident="S!B5", derived=DerivedInfo("formula", ("S!B4",), None, "=B4*2"))
    check = ReverseEngine._check_derived(t, {})
    assert check.consistent and "not recomputed" in check.explanation and "=B4*2" in check.explanation


def test_sources_outside_the_numbers_read_cannot_be_checked() -> None:
    t = target(62.0, ["Total"], ["V"], ident="S!B5", derived=DerivedInfo("formula", ("S!Z99",), "sum", "=SUM(Z99)"))
    assert ReverseEngine._check_derived(t, {}).consistent  # "not recomputed", never a false alarm


def test_a_typed_total_that_is_not_the_sum_of_its_parts_is_explained_by_the_data(orders) -> None:
    """Two regions are listed but the typed total includes East as well: the data reproduces it."""
    parts = [cell(300.75, "North", "S!B2"), cell(350.75, "South", "S!B3")]
    report = run(orders, [*parts, total(662.0, ["S!B2", "S!B3"], ident="S!B4")])
    result = by_id(report)["S!B4"]
    assert result.status == REPRODUCED  # the data explains it, even though it is not the sum of what is shown
    assert any("not what its own parts give" in note for note in result.notes)


def test_an_inconsistent_formula_total_stays_derived_and_is_flagged(orders) -> None:
    parts = [cell(300.75, "North", "S!B2"), cell(350.75, "South", "S!B3")]
    bad = target(700.0, ["Total"], ["Sales"], ident="S!B4", derived=DerivedInfo("formula", ("S!B2", "S!B3"), "sum", "=SUM(B2:B3)"))
    report = run(orders, [*parts, bad])
    result = by_id(report)["S!B4"]
    assert result.status == DERIVED and not result.derived_check.consistent and result.hint
    assert report.summary.suspected_errors == 1


# --- raw, cleaned, and the gate -----------------------------------------------------------


def test_a_number_that_only_the_cleaned_data_gives_is_marked_and_never_writable() -> None:
    raw = pd.DataFrame({"Region": ["North", "North", "North", "South", "South"], "Sales": [100.5, 9999.0, 40.25, 50.75, 20.5]})
    cleaned = pd.DataFrame({"Region": ["North", "North", "South", "South"], "Sales": [100.5, 40.25, 50.75, 20.5]})  # 9999 was a typo
    report = run(raw, [cell(140.75, "North", "S!B2"), cell(71.25, "South", "S!B3")], cleaned=cleaned)
    north = by_id(report)["S!B2"]
    assert north.status == REPRODUCED and north.basis == "cleaned" and not north.writable
    assert "only matches the cleaned data" in " ".join(north.notes)
    south = by_id(report)["S!B3"]
    assert south.basis == "raw" and south.writable  # matches both; raw wins


def test_the_cleaned_frame_is_not_consulted_when_raw_already_explains_everything(orders) -> None:
    report = run(orders, [cell(300.75, "North", "S!B2")], cleaned=orders.copy())
    assert by_id(report)["S!B2"].basis == "raw"


def test_a_candidate_the_gate_rejects_is_never_reproduced(orders) -> None:
    """If the search and verify() disagree (here: summing text), verify() has the last word."""
    frame = orders.assign(Region_Code=["1", "2", "x", "y", "z"])
    engine = ReverseEngine(frame, "Orders")
    bad = Candidate(Measure(Op.SUM, "Region_Code"), 3.0, "s", 10.0, "direct")
    resolution = consistency.Resolution(search=Synthesizer(DataIndex(frame)).search(target(3.0, ["X"], decimals=0, shown="3")), chosen=bad)
    result = engine._prove(resolution, frame, "raw")
    assert result.status == NOT_REPRODUCIBLE and result.expr is None
    assert any("was rejected" in note for note in result.notes)


def test_a_candidate_that_does_not_recompute_to_the_number_is_refused(orders) -> None:
    engine = ReverseEngine(orders, "Orders")
    wrong = Candidate(Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, "North"),)), 999.0, "s", 10.0, "direct")
    resolution = consistency.Resolution(search=Synthesizer(DataIndex(orders)).search(target(999.0, ["North"])), chosen=wrong)
    result = engine._prove(resolution, orders, "raw")
    assert result.status == NOT_REPRODUCIBLE and any("did not reproduce" in note for note in result.notes)


def test_a_candidate_that_recomputes_is_reproduced_with_dax_and_exactness(orders) -> None:
    good = Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, "North"),))
    resolution = consistency.Resolution(
        search=Synthesizer(DataIndex(orders)).search(target(300.75, ["North"])), chosen=Candidate(good, 300.75, shape_of(good), 10.0, "direct")
    )
    result = ReverseEngine(orders, "Orders")._prove(resolution, orders, "raw")
    assert result.status == REPRODUCED and result.dax == "CALCULATE(SUM('Orders'[Sales]), 'Orders'[Region] = \"North\")"
    assert result.recomputed == 300.75 and result.exact and result.writable and result.shape == shape_of(good)


# --- bounds and honesty -------------------------------------------------------------------


def test_a_spent_time_budget_is_reported_not_hidden(orders) -> None:
    report = run(orders, [cell(123456.5, "North", "S!B2", decimals=1), cell(1.25, "South", "S!B3")], time_budget=-1.0)
    assert report.summary.budget_exhausted
    assert all(any("time budget" in n for n in r.notes) for r in report.results if r.status != REPRODUCED)


def test_an_unexplainable_cell_alone_has_no_hint_but_says_why(orders) -> None:
    result = by_id(run(orders, [target(123456.5, ["Mars"], ["Mystery"], decimals=1, ident="S!B2")]))["S!B2"]
    assert result.status == NOT_REPRODUCIBLE and result.hint is None and result.closest is None
    assert any("No formula" in reason for reason in result.reasons)


def test_a_cell_whose_label_names_a_measure_gets_a_closest_reading(orders) -> None:
    result = by_id(run(orders, [target(999.0, ["North"], ["Sales"], decimals=1, ident="S!B2")]))["S!B2"]
    assert result.status == NOT_REPRODUCIBLE
    assert result.closest.value == pytest.approx(300.75) and "Region is North" in result.closest.formula
    assert "999.0" in result.hint


def test_ambiguous_cells_keep_every_alternative_and_are_not_writable() -> None:
    frame = pd.DataFrame({"Seg": ["Aa", "Aa", "Bb"], "ID": ["a1", "a2", "b1"], "Name": ["x1", "x2", "y1"], "Amount": [1.5, 2.5, 3.5]})
    report = run(frame, [target(2, ["Aa"], ["Customers"], decimals=0, shown="2", ident="S!B2")])
    result = by_id(report)["S!B2"]
    assert result.status == AMBIGUOUS and not result.writable and result.alternatives
    assert report.summary.ambiguous == 1 and report.summary.percent_reproduced == 0.0


def test_the_summary_excludes_derived_cells_from_the_percentage(orders) -> None:
    parts = [cell(300.75, "North", "S!B2"), cell(350.75, "South", "S!B3"), cell(10.5, "East", "S!B4")]
    report = run(orders, [*parts, total(662.0, ["S!B2", "S!B3", "S!B4"])])
    assert (report.summary.cells, report.summary.reproduced, report.summary.derived) == (4, 3, 1)
    assert report.summary.percent_reproduced == 100.0
