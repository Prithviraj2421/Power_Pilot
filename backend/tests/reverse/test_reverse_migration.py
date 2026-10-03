"""Turning proven numbers into measures: grouping, naming, and what is never offered."""

from __future__ import annotations

import pytest

from app.intelligence.kpi.compilers import DaxCompiler, PandasCompiler
from app.intelligence.kpi.ir import Compare, DatePart, Filter, Measure, Op, Ratio
from app.intelligence.kpi.verification import verify
from app.reverse.describe import canonical_filters, shape_of
from app.reverse.migration import DISPLAY_FOLDER, build_plan
from app.reverse.models import REPRODUCED, CellResult

from tests.reverse import legacy_reports as lr
from tests.reverse.conftest import target

DF = lr.golden()
TABLE = "Orders"
PC = PandasCompiler()


def proven(expr, rows, cols, ident, **kw) -> CellResult:
    """A REPRODUCED cell for ``expr``, with the DAX and value the real compilers give."""
    outcome = verify(expr, DF, TABLE)
    assert outcome.verified
    result = CellResult(
        target(outcome.value, rows, cols, ident=ident, **kw),
        REPRODUCED,
        basis="raw",
        expr=expr,
        dax=outcome.dax,
        recomputed=outcome.value,
        shape=shape_of(expr),
    )
    return result


def plan_for(results, **kw):
    return build_plan("rep1", TABLE, "legacy.xlsx", results, lambda e: PC.evaluate(e, DF), columns=list(DF.columns), **kw)


def sales(region, year):
    return Measure(Op.SUM, "Sales", canonical_filters((Filter("Region", Compare.EQ, region), Filter("Order Date", Compare.EQ, year, DatePart.YEAR))))


def region_year_results():
    return [
        proven(sales(region, year), [region], [str(year)], f"S!{'BC'[j]}{i}")
        for i, region in enumerate(["Central", "East"], start=3)
        for j, year in enumerate([2023, 2024])
    ]


def test_cells_following_one_rule_become_one_measure_with_the_varying_filters_dropped() -> None:
    plan = plan_for(region_year_results())
    assert len(plan.measures) == 1
    (measure,) = plan.measures
    assert measure.kind == "grouped" and measure.name == "Total Sales"
    assert measure.dax == "SUM('Orders'[Sales])"  # Region and Year come from the visual
    assert measure.expr == Measure(Op.SUM, "Sales")
    assert measure.cell_ids == ["S!B3", "S!C3", "S!B4", "S!C4"]
    assert "Region and Year of Order Date" in measure.notes[0] and "4 numbers" in measure.notes[0]


def test_every_cell_and_the_measure_itself_are_checks_for_the_engine() -> None:
    (measure,) = plan_for(region_year_results()).measures
    labels = [c.label for c in measure.checks]
    assert labels[0] == "the measure itself, with nothing filtered" and len(measure.checks) == 5
    assert measure.checks[0].expected == pytest.approx(float(DF["Sales"].sum())) and measure.checks[0].dax == measure.dax
    for check, cell in zip(measure.checks[1:], region_year_results()):
        assert check.dax == cell.dax and check.expected == cell.recomputed and check.cell_id == cell.target.id
        assert "CALCULATE" in check.dax  # each cell is checked with its own explicit filters


def test_a_filter_that_never_changes_is_kept() -> None:
    cells = [
        proven(Measure(Op.SUM, "Sales", canonical_filters((Filter("Region", Compare.EQ, "West"), Filter("Segment", Compare.EQ, s)))), [s], ["West"], f"S!B{i}")
        for i, s in enumerate(["Consumer", "Corporate"], start=2)
    ]
    (measure,) = plan_for(cells).measures
    assert measure.dax == "CALCULATE(SUM('Orders'[Sales]), 'Orders'[Region] = \"West\")"  # Segment varies; West is constant


def test_a_ratio_with_the_same_filters_on_both_sides_is_grouped() -> None:
    cells = []
    for i, category in enumerate(["Furniture", "Technology"], start=2):
        scope = (Filter("Category", Compare.EQ, category),)
        cells.append(proven(Ratio(Measure(Op.SUM, "Profit", scope), Measure(Op.SUM, "Sales", scope)), [category], ["Profit margin %"], f"S!B{i}", unit="percent", scale=0.01))
    (measure,) = plan_for(cells).measures
    assert measure.kind == "grouped" and measure.name == "Profit margin %"  # the report's own heading names it
    assert measure.dax == "DIVIDE(SUM('Orders'[Profit]), SUM('Orders'[Sales]))"


def test_a_share_of_total_is_written_per_cell_not_grouped() -> None:
    cells = []
    for i, region in enumerate(["Central", "East"], start=2):
        top = Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, region),))
        cells.append(proven(Ratio(top, Measure(Op.SUM, "Sales")), [region], ["Share"], f"S!B{i}", unit="percent", scale=0.01))
    plan = plan_for(cells)
    assert [m.kind for m in plan.measures] == ["single", "single"]  # dropping Region would also drop it from the numerator only
    assert plan.measures[0].name != plan.measures[1].name


def test_a_single_cell_gets_a_name_from_its_filters() -> None:
    cell = proven(sales("West", 2024), ["West"], ["2024"], "S!C6")
    (measure,) = plan_for([cell]).measures
    assert measure.kind == "single" and measure.name == "Total Sales - West - 2024"
    assert measure.dax == cell.dax and measure.cell_ids == ["S!C6"]


def test_identical_formulas_share_one_measure() -> None:
    cells = [proven(sales("West", 2024), ["West"], ["2024"], "S!B2"), proven(sales("West", 2024), ["West", "again"], ["2024"], "S!B9")]
    (measure,) = plan_for(cells).measures
    assert measure.kind == "single" and measure.cell_ids == ["S!B2", "S!B9"] and "2 numbers" in measure.notes[0]


def test_names_never_collide_with_columns_or_existing_measures_or_each_other() -> None:
    cell = proven(Measure(Op.SUM, "Sales"), ["Total"], ["Sales"], "S!B2")
    assert plan_for([cell]).measures[0].name == "Total Sales"
    taken = plan_for([cell], existing_names={"total sales"}).measures[0].name
    assert taken == "Total Sales (2)"
    under_a_column_name = [
        proven(Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, r),)), [r], ["Sales"], f"S!B{i}") for i, r in enumerate(["West", "East"], start=2)
    ]
    assert plan_for(under_a_column_name).measures[0].name == "Sales (2)"  # the heading says "Sales", but a measure may not share a column's name
    twice = plan_for([proven(sales("West", 2024), ["West"], ["2024"], "S!B2"), proven(Measure(Op.SUM, "Sales", canonical_filters((Filter("Region", Compare.EQ, "West"),))), ["West"], ["all"], "S!B3")])
    assert len({m.name for m in twice.measures}) == len(twice.measures)


def test_a_period_heading_does_not_name_the_measure() -> None:
    cells = [proven(Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, r),)), [r], ["2024"], f"S!B{i}") for i, r in enumerate(["West", "East"], start=2)]
    assert plan_for(cells).measures[0].name == "Total Sales"
    for heading in ("Q3", "Jan 2024", "FY2024", "March"):
        cells = [proven(Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, r),)), [r], [heading], f"S!B{i}") for i, r in enumerate(["West", "East"], start=2)]
        assert plan_for(cells).measures[0].name == "Total Sales", heading


def test_ids_are_unique_and_stable_slugs_of_the_names() -> None:
    plan = plan_for([proven(sales("West", 2024), ["West"], ["2024"], "S!B2"), proven(sales("East", 2023), ["East"], ["2023"], "S!B3")])
    assert plan.measures[0].id == "rep1:total-sales"  # grouped
    assert plan_for([proven(sales("West", 2024), ["West"], ["2024"], "S!B2")]).measures[0].id == "rep1:total-sales-west-2024"


def test_only_cells_proven_on_the_raw_data_take_part() -> None:
    raw = proven(sales("West", 2024), ["West"], ["2024"], "S!B2")
    cleaned = proven(sales("East", 2024), ["East"], ["2024"], "S!B3")
    cleaned.basis = "cleaned"
    from app.reverse.models import AMBIGUOUS, NOT_REPRODUCIBLE

    ambiguous = proven(sales("South", 2024), ["South"], ["2024"], "S!B4")
    ambiguous.status = AMBIGUOUS
    missed = CellResult(target(1.0, ["X"], ["Y"], ident="S!B5"), NOT_REPRODUCIBLE)
    plan = plan_for([raw, cleaned, ambiguous, missed])
    assert [c for m in plan.measures for c in m.cell_ids] == ["S!B2"]
    assert plan.not_writable == [{"cell": "S!B3", "reason": "it only matches the cleaned data, not the table in the model"}]


def test_the_plan_serialises_without_ir_objects() -> None:
    import json

    payload = json.loads(json.dumps(plan_for(region_year_results()).to_dict()))
    assert payload["table"] == "Orders" and payload["measures"][0]["display_folder"] == DISPLAY_FOLDER == "PowerPilot\\Migrated"
    assert payload["measures"][0]["formula"] == "Sum of Sales"


def test_the_written_dax_is_exactly_what_the_compiler_produces() -> None:
    (measure,) = plan_for(region_year_results()).measures
    assert measure.dax == DaxCompiler(TABLE).compile(measure.expr)


def test_a_measure_whose_dax_already_exists_just_covers_the_extra_cells() -> None:
    """"All Regions" by year is the same SUM(Sales) once the year comes from the visual: one measure, not two."""
    by_region = region_year_results()
    all_regions = [proven(lr.sales_by(None, year), ["All Regions"], [str(year)], f"S!{'BC'[j]}9") for j, year in enumerate([2023, 2024])]
    plan = plan_for([*by_region, *all_regions])

    assert [m.name for m in plan.measures] == ["Total Sales"]
    (measure,) = plan.measures
    assert measure.cell_ids == ["S!B3", "S!C3", "S!B4", "S!C4", "S!B9", "S!C9"] and measure.dax == "SUM('Orders'[Sales])"
    assert "all 6 numbers" in measure.notes[0] and "6 cells" in measure.description
    assert sum(1 for c in measure.checks if c.cell_id) == 6  # every extra cell is still engine-checked
    again = plan_for([proven(Measure(Op.SUM, "Sales", ()), ["x"], ["y"], "S!B1")], existing_names=set())
    assert again.measures[0].name == "Total Sales"  # the merged-away name was released, not leaked
