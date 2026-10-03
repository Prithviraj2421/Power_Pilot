import numpy as np
import pandas as pd
import pytest

import app.intelligence.kpi.verification as verification
from app.intelligence.kpi.ir import Compare, Difference, Filter, Measure, Op, Ratio, distinct, total
from app.intelligence.kpi.verification import verify


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sales": [10.0, 20.0, 30.0, 40.0],
            "cost": [0.0, 0.0, 0.0, 0.0],
            "order": ["a", "a", "b", "c"],
            "words": ["red", "green", "blue", "pink"],
            "mostly": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "n/a"][:4] ,
            "flag": [True, False, True, True],
            "when": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "gappy": [1.0, np.nan, 3.0, 4.0],
        }
    )


def test_a_sound_kpi_is_verified_with_its_value_and_dax(df) -> None:
    result = verify(Ratio(total("sales"), distinct("order")), df, "orders")

    assert result.verified
    assert result.value == pytest.approx(100 / 3)
    assert result.dax == "DIVIDE(SUM('orders'[sales]), DISTINCTCOUNT('orders'[order]))"
    assert "4 rows" in result.note


def test_a_missing_column_is_rejected_and_named(df) -> None:
    result = verify(total("Sales_Amount"), df, "orders")

    assert not result.verified and result.value is None
    assert "'Sales_Amount'" in result.note


def test_a_missing_filter_column_is_rejected_too(df) -> None:
    result = verify(Measure(Op.SUM, "sales", Filter("nope", Compare.EQ, "x")), df, "orders")

    assert not result.verified and "'nope'" in result.note


@pytest.mark.parametrize("column", ["words", "flag", "when"])
def test_summing_a_non_numeric_column_is_rejected(df, column: str) -> None:
    result = verify(total(column), df, "orders")

    assert not result.verified
    assert column in result.note


def test_a_mostly_numeric_text_column_is_accepted_and_the_blanks_are_reported() -> None:
    frame = pd.DataFrame({"sqft": [str(i) for i in range(1, 20)] + ["2100-2850"]})

    result = verify(total("sqft"), frame, "homes")

    assert result.verified and result.value == sum(range(1, 20))
    assert "1 non-numeric value(s) in 'sqft' count as blank" in result.note


def test_a_column_that_is_mostly_text_is_rejected() -> None:
    frame = pd.DataFrame({"mixed": ["1", "2"] + ["abc"] * 8})

    result = verify(total("mixed"), frame, "t")

    assert not result.verified and "20%" in result.note


def test_counting_and_distinct_counting_accept_any_type(df) -> None:
    assert verify(Measure(Op.COUNT, "words"), df, "t").value == 4.0
    assert verify(distinct("flag"), df, "t").value == 2.0
    assert verify(Measure(Op.COUNT), df, "t").value == 4.0


def test_division_by_zero_is_rejected_not_reported_as_infinity(df) -> None:
    result = verify(Ratio(total("sales"), total("cost")), df, "orders")

    assert not result.verified and "BLANK" in result.note


def test_an_expression_matching_no_rows_is_rejected(df) -> None:
    result = verify(Measure(Op.SUM, "sales", Filter("order", Compare.EQ, "zzz")), df, "orders")

    assert not result.verified and "BLANK" in result.note


def test_a_column_with_no_values_is_rejected() -> None:
    result = verify(total("empty"), pd.DataFrame({"empty": [None, None]}, dtype="float64"), "t")

    assert not result.verified and "no values" in result.note


def test_infinity_is_rejected() -> None:
    result = verify(total("big"), pd.DataFrame({"big": [np.inf, 1.0]}), "t")

    assert not result.verified and "finite" in result.note


def test_a_grouped_measure_is_not_a_kpi(df) -> None:
    result = verify(Measure(Op.SUM, "sales", group="order"), df, "orders")

    assert not result.verified and "single value" in result.note


def test_ordered_filters_need_a_numeric_column(df) -> None:
    result = verify(Measure(Op.SUM, "sales", Filter("words", Compare.GT, 3)), df, "orders")

    assert not result.verified and "words" in result.note


def test_filters_that_compare_blanks_are_refused_because_dax_treats_them_differently(df) -> None:
    for compare in (Compare.GT, Compare.LE, Compare.NE):
        result = verify(Measure(Op.SUM, "sales", Filter("gappy", compare, 2)), df, "orders")
        assert not result.verified and "blank" in result.note

    assert verify(Measure(Op.SUM, "sales", Filter("gappy", Compare.EQ, 3.0)), df, "orders").verified


def test_a_difference_of_verified_parts_is_verified(df) -> None:
    result = verify(Difference(total("sales"), total("cost")), df, "orders")

    assert result.verified and result.value == 100.0


def test_if_the_dax_compiler_and_the_expression_ever_disagree_the_kpi_is_rejected(df, monkeypatch) -> None:
    class Wrong:
        def __init__(self, table: str) -> None:
            pass

        def compile(self, expr) -> str:
            return "SUM('orders'[sales]) + SUM('orders'[cost])"  # reads a column the expression does not

    monkeypatch.setattr(verification, "DaxCompiler", Wrong)

    result = verify(total("sales"), df, "orders")

    assert not result.verified and "does not match" in result.note


def test_a_dax_table_that_is_not_the_models_table_is_rejected(df, monkeypatch) -> None:
    class Wrong:
        def __init__(self, table: str) -> None:
            pass

        def compile(self, expr) -> str:
            return "SUM('orders.csv'[sales])"

    monkeypatch.setattr(verification, "DaxCompiler", Wrong)

    assert not verify(total("sales"), df, "orders").verified


def test_a_computation_that_raises_is_rejected_not_propagated(df, monkeypatch) -> None:
    class Boom:
        def evaluate(self, expr, frame):
            raise RuntimeError("boom")

    monkeypatch.setattr(verification, "PandasCompiler", Boom)

    result = verify(total("sales"), df, "orders")

    assert not result.verified and "boom" in result.note


def test_a_row_count_references_the_table_and_no_column_and_still_verifies(df) -> None:
    result = verify(Measure(Op.COUNT), df, "t")

    assert result.verified and result.value == 4.0 and result.dax == "COUNTROWS('t')"
