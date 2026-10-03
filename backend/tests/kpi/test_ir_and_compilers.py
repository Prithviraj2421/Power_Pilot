import math

import pandas as pd
import pytest

from app.intelligence.kpi.compilers import DaxCompiler, PandasCompiler
from app.intelligence.kpi.ir import (
    Compare,
    Difference,
    Filter,
    Measure,
    Op,
    Ratio,
    average,
    columns_of,
    distinct,
    total,
)

DAX = DaxCompiler("Sales_Data")
PANDAS = PandasCompiler()


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "amount": [10.0, 20.0, None, 40.0],
            "units": [1, 2, 3, 4],
            "region": ["East", "West", "East", None],
            "order": ["A", "A", "B", "C"],
            "label": ["x", "5", "7.5", "oops"],
        }
    )


# --- IR ---------------------------------------------------------------------------------


def test_a_measure_that_aggregates_needs_a_column() -> None:
    for op in (Op.SUM, Op.AVERAGE, Op.MIN, Op.MAX, Op.DISTINCT_COUNT):
        with pytest.raises(ValueError, match="needs a column"):
            Measure(op)


def test_count_without_a_column_counts_rows_and_ratio_is_not_a_measure() -> None:
    assert Measure(Op.COUNT).column is None
    with pytest.raises(ValueError, match="use Ratio"):
        Measure(Op.RATIO, "amount")


def test_in_filters_take_a_tuple_and_others_take_a_scalar() -> None:
    with pytest.raises(ValueError):
        Filter("region", Compare.IN, "East")
    with pytest.raises(ValueError):
        Filter("region", Compare.EQ, ("East",))


def test_columns_of_lists_every_column_once_in_first_use_order() -> None:
    expr = Ratio(
        Measure(Op.SUM, "amount", Filter("region", Compare.EQ, "East")),
        Difference(total("amount"), distinct("order")),
    )
    assert columns_of(expr) == ("amount", "region", "order")


# --- DAX compiler: every op ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("expr", "dax"),
    [
        (Measure(Op.SUM, "amount"), "SUM('Sales_Data'[amount])"),
        (Measure(Op.AVERAGE, "amount"), "AVERAGE('Sales_Data'[amount])"),
        (Measure(Op.MIN, "amount"), "MIN('Sales_Data'[amount])"),
        (Measure(Op.MAX, "amount"), "MAX('Sales_Data'[amount])"),
        (Measure(Op.COUNT, "order"), "COUNTA('Sales_Data'[order])"),
        (Measure(Op.COUNT), "COUNTROWS('Sales_Data')"),
        (Measure(Op.DISTINCT_COUNT, "order"), "DISTINCTCOUNT('Sales_Data'[order])"),
        (Ratio(total("amount"), distinct("order")), "DIVIDE(SUM('Sales_Data'[amount]), DISTINCTCOUNT('Sales_Data'[order]))"),
        (Ratio(total("amount"), total("units"), scale=100), "DIVIDE(SUM('Sales_Data'[amount]), SUM('Sales_Data'[units])) * 100"),
        (Difference(total("amount"), total("units")), "SUM('Sales_Data'[amount]) - SUM('Sales_Data'[units])"),
    ],
)
def test_dax_for_every_op(expr, dax: str) -> None:
    assert DAX.compile(expr) == dax


def test_dax_filters_and_literals() -> None:
    assert (
        DAX.compile(Measure(Op.SUM, "amount", Filter("region", Compare.EQ, "East")))
        == "CALCULATE(SUM('Sales_Data'[amount]), 'Sales_Data'[region] = \"East\")"
    )
    assert "<> \"a\"\"b\"" in DAX.compile(Measure(Op.SUM, "amount", Filter("region", Compare.NE, 'a"b')))
    assert ">= 0.5" in DAX.compile(Measure(Op.SUM, "amount", Filter("units", Compare.GE, 0.5)))
    assert "IN {\"East\", \"West\"}" in DAX.compile(Measure(Op.SUM, "amount", Filter("region", Compare.IN, ("East", "West"))))
    assert "= TRUE()" in DAX.compile(Measure(Op.SUM, "amount", Filter("flag", Compare.EQ, True)))


def test_dax_escapes_awkward_names() -> None:
    assert DaxCompiler("T").compile(total("Sub-Category ]x")) == "SUM('T'[Sub-Category ]]x])"
    assert DaxCompiler("O'Brien").compile(total("a")) == "SUM('O''Brien'[a])"


def test_a_subtracted_difference_is_parenthesised() -> None:
    expr = Difference(total("a"), Difference(total("b"), total("c")))
    assert DAX.compile(expr) == "SUM('Sales_Data'[a]) - (SUM('Sales_Data'[b]) - SUM('Sales_Data'[c]))"


def test_grouped_measures_are_queries_not_measures() -> None:
    grouped = Measure(Op.SUM, "amount", group="region")
    with pytest.raises(ValueError, match="compile_query"):
        DAX.compile(grouped)
    assert (
        DAX.compile_query(grouped, "Amount by region")
        == "SUMMARIZECOLUMNS('Sales_Data'[region], \"Amount by region\", SUM('Sales_Data'[amount]))"
    )
    with pytest.raises(ValueError):
        DAX.compile_query(total("amount"))


# --- pandas compiler: every op and the BLANK rules ----------------------------------------


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        (Measure(Op.SUM, "amount"), 70.0),
        (Measure(Op.AVERAGE, "amount"), 70.0 / 3),
        (Measure(Op.MIN, "amount"), 10.0),
        (Measure(Op.MAX, "amount"), 40.0),
        (Measure(Op.COUNT, "amount"), 3.0),
        (Measure(Op.COUNT), 4.0),
        (Measure(Op.DISTINCT_COUNT, "order"), 3.0),
        (Ratio(total("amount"), total("units")), 7.0),
        (Ratio(total("units"), total("amount"), scale=100), 10 / 70 * 100),
        (Difference(total("amount"), total("units")), 60.0),
    ],
)
def test_pandas_value_for_every_op(df, expr, expected: float) -> None:
    assert PANDAS.evaluate(expr, df) == pytest.approx(expected)


def test_distinct_count_counts_blank_as_a_value_like_dax() -> None:
    assert PANDAS.evaluate(distinct("region"), pd.DataFrame({"region": ["East", None, "East", None]})) == 2.0


def test_text_that_is_not_a_number_counts_as_blank() -> None:
    frame = pd.DataFrame({"label": ["x", "5", "7.5", "oops"]})
    assert PANDAS.evaluate(total("label"), frame) == 12.5


def test_filters_in_pandas(df) -> None:
    assert PANDAS.evaluate(Measure(Op.SUM, "units", Filter("region", Compare.EQ, "East")), df) == 4.0
    assert PANDAS.evaluate(Measure(Op.SUM, "units", Filter("region", Compare.IN, ("East", "West"))), df) == 6.0
    assert PANDAS.evaluate(Measure(Op.SUM, "units", Filter("units", Compare.GT, 2)), df) == 7.0
    assert PANDAS.evaluate(Measure(Op.SUM, "units", Filter("units", Compare.LE, 2)), df) == 3.0


def test_blank_rules_follow_dax(df) -> None:
    empty = Filter("region", Compare.EQ, "nowhere")
    assert PANDAS.evaluate(Measure(Op.SUM, "units", empty), df) is None, "no rows is BLANK"
    assert PANDAS.evaluate(Ratio(total("units"), Measure(Op.SUM, "units", empty)), df) is None
    assert PANDAS.evaluate(Ratio(total("units"), Measure(Op.SUM, "amount", Filter("units", Compare.GT, 99))), df) is None
    assert PANDAS.evaluate(Ratio(total("units"), Measure(Op.MIN, "units", Filter("units", Compare.LT, 1))), df) is None
    # A BLANK operand acts as 0 in subtraction, unless both are BLANK.
    assert PANDAS.evaluate(Difference(total("units"), Measure(Op.SUM, "units", empty)), df) == 10.0
    assert PANDAS.evaluate(Difference(Measure(Op.SUM, "units", empty), total("units")), df) == -10.0
    assert PANDAS.evaluate(Difference(Measure(Op.SUM, "units", empty), Measure(Op.SUM, "units", empty)), df) is None


def test_division_by_zero_is_blank_not_infinity() -> None:
    frame = pd.DataFrame({"a": [1.0, 2.0], "b": [0.0, 0.0]})
    assert PANDAS.evaluate(Ratio(total("a"), total("b")), frame) is None


def test_grouped_evaluation(df) -> None:
    grouped = PANDAS.evaluate_grouped(Measure(Op.SUM, "units", group="region"), df)
    assert grouped["East"] == 4.0 and grouped["West"] == 2.0
    assert math.isnan(next(k for k in grouped if isinstance(k, float) and math.isnan(k)))
    with pytest.raises(ValueError):
        PANDAS.evaluate(Measure(Op.SUM, "units", group="region"), df)
    with pytest.raises(ValueError):
        PANDAS.evaluate_grouped(total("units"), df)
