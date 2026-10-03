"""Date-part filters (YEAR/QUARTER/MONTH) and several filters per measure, in both compilers and the gate."""

from __future__ import annotations

import datetime as dt
import random

import pandas as pd
import pytest

from app.intelligence.kpi.compilers import DaxCompiler, PandasCompiler
from app.intelligence.kpi.ir import Compare, DatePart, Filter, Measure, Op, columns_of
from app.intelligence.kpi.verification import verify

from tests.kpi.dax_oracle import evaluate_dax
from tests.kpi.test_dax_pandas_agreement import agree, rows_of

DAX = DaxCompiler("Orders")
PANDAS = PandasCompiler()


@pytest.fixture
def orders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "when": pd.to_datetime(["2023-12-31", "2024-01-15", "2024-04-02", "2024-08-30", "2025-02-01"]),
            "region": ["East", "East", "West", "West", "East"],
            "sales": [10.0, 20.0, 30.0, 40.0, 50.0],
            "ids": ["a", "b", "c", "a", "d"],
        }
    )


def year(value: int, compare: Compare = Compare.EQ) -> Filter:
    return Filter("when", compare, value, DatePart.YEAR)


# --- IR ---------------------------------------------------------------------------------


def test_a_lone_filter_or_none_is_normalised_to_a_tuple() -> None:
    flt = Filter("region", Compare.EQ, "East")
    assert Measure(Op.SUM, "sales", flt).filters == (flt,)
    assert Measure(Op.SUM, "sales", None).filters == ()
    assert Measure(Op.SUM, "sales").filters == ()
    assert Measure(Op.SUM, "sales", [flt, year(2024)]).filters == (flt, year(2024))
    with pytest.raises(ValueError, match="Filter objects"):
        Measure(Op.SUM, "sales", ("East",))


def test_a_date_part_filter_compares_with_whole_numbers_only() -> None:
    for bad in ("2024", 2024.5, True):
        with pytest.raises(ValueError, match="whole numbers"):
            Filter("when", Compare.EQ, bad, DatePart.YEAR)
    with pytest.raises(ValueError, match="whole numbers"):
        Filter("when", Compare.IN, (2024, "x"), DatePart.YEAR)
    assert Filter("when", Compare.EQ, 2024.0, DatePart.YEAR)  # a float that is a whole number is fine


def test_columns_of_sees_every_filter_column() -> None:
    expr = Measure(Op.SUM, "sales", (Filter("region", Compare.EQ, "East"), year(2024)))
    assert columns_of(expr) == ("sales", "region", "when")


# --- DAX --------------------------------------------------------------------------------


def test_dax_for_each_date_part_and_for_several_filters() -> None:
    assert DAX.compile(Measure(Op.SUM, "sales", year(2024))) == "CALCULATE(SUM('Orders'[sales]), YEAR('Orders'[when]) = 2024)"
    assert "QUARTER('Orders'[when]) >= 3" in DAX.compile(
        Measure(Op.SUM, "sales", Filter("when", Compare.GE, 3, DatePart.QUARTER))
    )
    assert "MONTH('Orders'[when]) IN {1, 2}" in DAX.compile(
        Measure(Op.SUM, "sales", Filter("when", Compare.IN, (1, 2), DatePart.MONTH))
    )
    both = Measure(Op.SUM, "sales", (Filter("region", Compare.EQ, "West"), year(2024)))
    assert DAX.compile(both) == (
        "CALCULATE(SUM('Orders'[sales]), 'Orders'[region] = \"West\", YEAR('Orders'[when]) = 2024)"
    )


# --- pandas -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("flt", "expected"),
    [
        (year(2024), 90.0),
        (year(2024, Compare.NE), 60.0),
        (year(2024, Compare.GT), 50.0),
        (year(2024, Compare.GE), 140.0),
        (year(2024, Compare.LT), 10.0),
        (year(2024, Compare.LE), 100.0),
        (Filter("when", Compare.IN, (2023, 2025), DatePart.YEAR), 60.0),
        (Filter("when", Compare.EQ, 1, DatePart.QUARTER), 70.0),
        (Filter("when", Compare.EQ, 4, DatePart.QUARTER), 10.0),
        (Filter("when", Compare.EQ, 8, DatePart.MONTH), 40.0),
        (Filter("when", Compare.IN, (1, 12), DatePart.MONTH), 30.0),
    ],
)
def test_each_date_part_and_comparison_in_pandas(orders, flt, expected) -> None:
    assert PANDAS.evaluate(Measure(Op.SUM, "sales", flt), orders) == expected


def test_several_filters_are_anded(orders) -> None:
    east_2024 = Measure(Op.SUM, "sales", (Filter("region", Compare.EQ, "East"), year(2024)))
    assert PANDAS.evaluate(east_2024, orders) == 20.0
    assert PANDAS.evaluate(Measure(Op.SUM, "sales", (year(2024), year(2025))), orders) is None  # contradiction -> BLANK


def test_text_dates_are_read_day_first_when_that_is_the_only_consistent_reading() -> None:
    frame = pd.DataFrame({"when": ["28/11/2015", "03/01/2016", "15/12/2015"], "sales": [1.0, 2.0, 4.0]})
    assert PANDAS.evaluate(Measure(Op.SUM, "sales", year(2015)), frame) == 5.0
    assert PANDAS.evaluate(Measure(Op.SUM, "sales", Filter("when", Compare.EQ, 1, DatePart.MONTH)), frame) == 2.0


def test_grouped_measures_honour_every_filter(orders) -> None:
    grouped = Measure(Op.SUM, "sales", (year(2024), Filter("region", Compare.EQ, "West")), group="region")
    assert PANDAS.evaluate_grouped(grouped, orders) == {"West": 70.0}


# --- the gate ---------------------------------------------------------------------------


def test_verify_accepts_date_part_filters_on_real_dates(orders) -> None:
    result = verify(Measure(Op.SUM, "sales", year(2024)), orders, "Orders")
    assert result.verified and result.value == 90.0
    assert "YEAR('Orders'[when]) = 2024" in result.dax


def test_verify_says_so_when_dates_are_text_and_names_the_basis() -> None:
    frame = pd.DataFrame({"when": ["2024-01-05", "2024-03-09"], "sales": [1.0, 2.0]})
    result = verify(Measure(Op.SUM, "sales", year(2024)), frame, "Orders", basis="Power BI table")
    assert result.verified
    assert "holds dates as text" in result.note and "Power BI table" in result.note and "cleaned" not in result.note


def test_verify_refuses_date_filters_on_non_dates_and_on_unreadable_text(orders) -> None:
    numbers = verify(Measure(Op.SUM, "sales", Filter("sales", Compare.EQ, 2024, DatePart.YEAR)), orders, "Orders")
    assert not numbers.verified and "not a date" in numbers.note
    junk = pd.DataFrame({"when": ["2024-01-05", "soon"], "sales": [1.0, 2.0]})
    result = verify(Measure(Op.SUM, "sales", year(2024)), junk, "Orders")
    assert not result.verified and "cannot be read as dates" in result.note


def test_verify_refuses_ordered_date_filters_when_dates_are_blank() -> None:
    frame = pd.DataFrame({"when": pd.to_datetime(["2024-01-05", None]), "sales": [1.0, 2.0]})
    assert verify(Measure(Op.SUM, "sales", year(2024)), frame, "Orders").verified
    for compare in (Compare.NE, Compare.GE):
        result = verify(Measure(Op.SUM, "sales", year(2024, compare)), frame, "Orders")
        assert not result.verified and "blank" in result.note


def test_verify_checks_every_filter_not_just_the_first(orders) -> None:
    result = verify(Measure(Op.SUM, "sales", (Filter("region", Compare.EQ, "East"), Filter("nope", Compare.EQ, 1))), orders, "Orders")
    assert not result.verified and "nope" in result.note


# --- DAX text and pandas value agree (independent oracle) ----------------------------------


def random_dated_filter(rng: random.Random) -> Filter:
    part = rng.choice(list(DatePart))
    top = {DatePart.YEAR: (2022, 2025), DatePart.QUARTER: (1, 4), DatePart.MONTH: (1, 12)}[part]
    compare = rng.choice(list(Compare))
    if compare is Compare.IN:
        return Filter("when", compare, tuple(rng.sample(range(top[0], top[1] + 1), rng.randint(1, 2))), part)
    return Filter("when", compare, rng.randint(*top), part)


@pytest.mark.parametrize("seed", range(8))
def test_dax_and_pandas_agree_on_random_date_and_multi_filter_measures(seed: int) -> None:
    rng = random.Random(seed)
    values = 0
    for _ in range(40):
        rows = rng.choice([1, 5, 40, 150])
        start = dt.date(2022, 1, 1)
        frame = pd.DataFrame(
            {
                "when": pd.to_datetime([start + dt.timedelta(days=rng.randint(0, 1400)) for _ in range(rows)]),
                "region": [rng.choice(["N", "S", "E"]) for _ in range(rows)],
                "sales": [round(rng.uniform(1, 99), 2) for _ in range(rows)],
            }
        )
        filters = [random_dated_filter(rng) for _ in range(rng.randint(1, 2))]
        if rng.random() < 0.5:
            filters.append(Filter("region", Compare.EQ, rng.choice(["N", "S", "E"])))
        expr = Measure(rng.choice([Op.SUM, Op.AVERAGE, Op.MIN, Op.MAX, Op.COUNT]), "sales", tuple(filters))

        expected = PANDAS.evaluate(expr, frame)
        dax_rows = [{k: (v.to_pydatetime() if isinstance(v, pd.Timestamp) else v) for k, v in r.items()} for r in rows_of(frame)]
        actual = evaluate_dax(DAX.compile(expr), dax_rows)
        assert agree(expected, actual), f"{DAX.compile(expr)}\n pandas={expected!r} oracle={actual!r}"
        values += expected is not None
    assert values > 10
