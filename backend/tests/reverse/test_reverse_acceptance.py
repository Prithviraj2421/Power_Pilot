"""End to end: a legacy report built from known formulas, with three planted mistakes.

The same report is written as .xlsx, .csv and .pdf and reverse-engineered against the raw data. The
bar (from the feature's brief): at least 95% of the correct numbers REPRODUCED *with the correct
formula*, each planted mistake NOT_REPRODUCIBLE with a sensible hint, and the Total row DERIVED.
"""

from __future__ import annotations

import json

import pytest

from app.intelligence.kpi.ir import Compare, DatePart, Filter, Measure, Op, Ratio
from app.reverse.describe import canonical_filters
from app.reverse.engine import ReverseEngine
from app.reverse.models import AMBIGUOUS, DERIVED, NOT_REPRODUCIBLE, REPRODUCED
from app.reverse.report_reader import read_report

from tests.reverse import legacy_reports as lr

FORMATS = {"xlsx": lr.to_xlsx, "csv": lr.to_csv, "pdf": lr.to_pdf}


def normalised(expr):
    """The formula with filters in a fixed order, so equal formulas compare equal."""
    if isinstance(expr, Measure):
        return Measure(expr.op, expr.column, canonical_filters(expr.filters), expr.group)
    if isinstance(expr, Ratio):
        return Ratio(normalised(expr.numerator), normalised(expr.denominator), expr.scale)
    return expr


@pytest.fixture(scope="module")
def report_spec():
    return lr.build()


@pytest.fixture(scope="module", params=sorted(FORMATS))
def run(request, report_spec):
    parsed = read_report(FORMATS[request.param](report_spec), f"legacy.{request.param}")
    report = ReverseEngine(report_spec.df, "Orders").run(parsed, f"legacy.{request.param}", "r1")
    by_cell = {(r.target.row_labels[-1], r.target.col_labels[-1] if r.target.col_labels else ""): r for r in report.results}
    return report, by_cell


def result_for(by_cell, cell: lr.Cell):
    return by_cell[(cell.row, cell.col)]


def test_every_number_in_the_report_is_found(run, report_spec) -> None:
    report, _ = run
    assert len(report.results) == len(report_spec.cells) == 22


def test_at_least_95_percent_of_the_correct_numbers_are_reproduced_with_the_right_formula(run, report_spec) -> None:
    _, by_cell = run
    correct = [c for c in report_spec.cells if c.mistake is None and c.formula is None]
    assert len(correct) == 17
    right = 0
    for cell in correct:
        result = result_for(by_cell, cell)
        if result.status == REPRODUCED and normalised(result.expr) == normalised(cell.expected):
            right += 1
        else:
            print("MISSED", cell.table, cell.row, cell.col, result.status, result.formula)
    assert right / len(correct) >= 0.95


def test_the_order_date_not_the_ship_date_is_chosen_where_only_neighbours_can_tell(run, report_spec) -> None:
    """South's sales differ by order year and ship year; every other cell fits both columns."""
    _, by_cell = run
    for year in (2023, 2024):
        result = result_for(by_cell, report_spec.cell(lr.T1, "South", str(year)))
        assert result.status == REPRODUCED
        assert Filter("Order Date", Compare.EQ, year, DatePart.YEAR) in result.expr.filters


def test_the_customer_counts_use_customer_id_not_customer_name(run, report_spec) -> None:
    """Customer Name fits two of three segments by chance; Customer ID fits all three."""
    _, by_cell = run
    for segment in lr.SEGMENTS:
        result = result_for(by_cell, report_spec.cell(lr.T3, segment, "Customers"))
        assert result.status == REPRODUCED and result.expr.column == "Customer ID"


@pytest.mark.parametrize(
    ("mistake", "table", "row", "col", "words"),
    [
        ("swapped-digits", lr.T1, "East", "2024", ["swapped", "16,079.19", "16,097.19"]),
        ("one-order", lr.T1, "Central", "2023", ["order", "Order ID"]),
        ("missing-region", lr.T1, "All Regions", "2024", ["Region", "West"]),
    ],
)
def test_each_planted_mistake_is_not_reproducible_with_a_sensible_hint(run, report_spec, mistake, table, row, col, words) -> None:
    _, by_cell = run
    cell = report_spec.cell(table, row, col)
    assert cell.mistake == mistake
    result = result_for(by_cell, cell)
    assert result.status == NOT_REPRODUCIBLE and result.expr is None and not result.writable
    for word in words:
        assert word.casefold() in result.hint.casefold(), (mistake, result.hint)
    # and the closest candidate is what the rule used by the neighbours gives
    assert result.closest is not None
    assert result.closest.value == pytest.approx(lr.PC.evaluate(cell_expected_for(report_spec, cell), report_spec.df))


def cell_expected_for(spec, cell):
    year = int(cell.col)
    return lr.sales_by(None if cell.row == "All Regions" else cell.row, year)


def test_the_total_row_is_derived_and_checked_against_its_own_parts(run, report_spec) -> None:
    _, by_cell = run
    for year in (2023, 2024):
        result = result_for(by_cell, report_spec.cell(lr.T1, "Total", str(year)))
        assert result.status == DERIVED and result.derived_check.consistent
        assert result.derived_check.expected == pytest.approx(report_spec.cell(lr.T1, "Total", str(year)).value, abs=0.01)
        assert not result.writable


def test_a_total_that_adds_up_but_disagrees_with_the_data_says_so(run, report_spec) -> None:
    """The totals sum the report's own (mistaken) cells, so they inherit the planted mistakes."""
    _, by_cell = run
    total_2023 = result_for(by_cell, report_spec.cell(lr.T1, "Total", "2023")).derived_check
    total_2024 = result_for(by_cell, report_spec.cell(lr.T1, "Total", "2024")).derived_check
    assert total_2023.matches_data is False and total_2024.matches_data is False
    assert total_2023.data_value == pytest.approx(lr.PC.evaluate(lr.sales_by(None, 2023), report_spec.df))


def test_nothing_unproven_can_be_written_to_power_bi(run) -> None:
    report, _ = run
    for result in report.results:
        assert result.writable == (result.status == REPRODUCED and result.basis == "raw")
        if result.writable:
            assert result.dax and result.recomputed is not None


def test_the_summary_counts_what_happened(run) -> None:
    report, _ = run
    s = report.summary
    assert (s.cells, s.reproduced, s.ambiguous, s.not_reproducible, s.derived) == (22, 17, 0, 3, 2)
    assert s.percent_reproduced == 85.0  # 17 of the 20 numbers that had to come from the data
    assert s.suspected_errors == 5  # three mistakes plus two totals that inherit them
    assert not s.budget_exhausted and s.seconds < 30


def test_the_whole_report_is_json_serialisable(run) -> None:
    report, _ = run
    payload = json.loads(json.dumps(report.to_dict()))
    assert payload["summary"]["reproduced"] == 17 and len(payload["cells"]) == 22
    assert {cell["status"] for cell in payload["cells"]} <= {REPRODUCED, AMBIGUOUS, NOT_REPRODUCIBLE, DERIVED}
    assert payload["layout"][0]["cells"], "the page needs the layout to draw the report back"
    reproduced = next(c for c in payload["cells"] if c["status"] == REPRODUCED)
    assert reproduced["dax"].startswith(("SUM", "CALCULATE", "DIVIDE", "DISTINCTCOUNT", "AVERAGE")) and reproduced["ir"]["type"] in {"measure", "ratio"}


def test_a_clean_report_has_nothing_flagged() -> None:
    spec = lr.build(mistakes=False)
    parsed = read_report(lr.to_xlsx(spec), "clean.xlsx")
    report = ReverseEngine(spec.df, "Orders").run(parsed, "clean.xlsx", "r")
    assert report.summary.not_reproducible == 0 and report.summary.ambiguous == 0
    assert report.summary.suspected_errors == 0 and report.summary.percent_reproduced == 100.0
    totals = [r for r in report.results if r.status == DERIVED]
    assert len(totals) == 2 and all(r.derived_check.matches_data for r in totals)
