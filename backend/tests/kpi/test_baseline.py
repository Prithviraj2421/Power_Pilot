import pandas as pd
import pytest

from app.intelligence.kpi.baseline import period_baseline
from app.intelligence.kpi.ir import Ratio, distinct, total


def frame(dates: list[str], sales: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"when": dates, "sales": sales, "order": [f"o{i}" for i in range(len(dates))]})


def test_latest_month_is_compared_with_the_month_before_it() -> None:
    df = frame(["2024-01-10", "2024-01-31", "2024-02-05", "2024-02-29"], [100.0, 100.0, 150.0, 150.0])

    baseline = period_baseline(total("sales"), df, "when")

    assert baseline.current == 300.0 and baseline.previous == 200.0
    assert baseline.change_pct == pytest.approx(50.0)
    assert baseline.text == "Latest month 2024-02 vs 2024-01: 300.00 vs 200.00 (+50.0%)"


def test_a_decline_is_signed() -> None:
    df = frame(["2024-01-31", "2024-02-29"], [200.0, 150.0])

    assert "(-25.0%)" in period_baseline(total("sales"), df, "when").text


def test_a_partial_latest_month_is_left_out_not_compared_as_if_complete() -> None:
    df = frame(["2024-01-31", "2024-02-29", "2024-03-04"], [100.0, 150.0, 1.0])

    baseline = period_baseline(total("sales"), df, "when")

    assert baseline.text.startswith("Latest complete month 2024-02 vs 2024-01: 150.00 vs 100.00 (+50.0%)")
    assert "2024-03 left out because its data ends 2024-03-04" in baseline.text


def test_with_only_one_complete_month_there_is_no_honest_baseline() -> None:
    assert period_baseline(total("sales"), frame(["2024-01-31", "2024-02-10"], [100.0, 40.0]), "when") is None


def test_a_month_that_is_nearly_complete_counts_as_complete() -> None:
    df = frame(["2024-11-30", "2024-12-30"], [100.0, 90.0])  # Dec 30 of 31

    assert period_baseline(total("sales"), df, "when").text.startswith("Latest month 2024-12 vs 2024-11")


def test_ratios_are_evaluated_inside_each_month() -> None:
    df = frame(["2024-01-15", "2024-01-31", "2024-02-15", "2024-02-29"], [10.0, 30.0, 30.0, 90.0])

    baseline = period_baseline(Ratio(total("sales"), distinct("order")), df, "when")

    assert (baseline.previous, baseline.current) == (20.0, 60.0)


def test_day_first_dates_are_understood() -> None:
    df = frame(["28/01/2024", "29/02/2024"], [100.0, 120.0])

    assert period_baseline(total("sales"), df, "when").text.startswith("Latest month 2024-02 vs 2024-01")


def test_a_single_month_has_no_baseline() -> None:
    assert period_baseline(total("sales"), frame(["2024-03-01", "2024-03-20"], [1.0, 2.0]), "when") is None


def test_no_parseable_dates_means_no_baseline() -> None:
    assert period_baseline(total("sales"), frame(["soon", "later"], [1.0, 2.0]), "when") is None


def test_a_zero_previous_value_gives_values_without_a_percentage() -> None:
    df = frame(["2024-01-31", "2024-02-29"], [0.0, 50.0])

    baseline = period_baseline(total("sales"), df, "when")

    assert baseline.change_pct is None and "%" not in baseline.text.split(";")[0]
