import pandas as pd

from app.common.date_parse import parse_dates_robust


def test_parses_day_first_dates_that_month_first_would_mostly_lose() -> None:
    # Every value has day > 12, so a naive month-first pd.to_datetime call
    # (pandas' default) would return NaT for all of them.
    series = pd.Series(["28/11/2015", "13/06/2016", "25/01/2017"])
    parsed = parse_dates_robust(series)

    assert parsed.notna().sum() == 3
    assert parsed.iloc[0] == pd.Timestamp("2015-11-28")


def test_still_parses_month_first_dates_correctly() -> None:
    # Unambiguous month-first values (day <= 12) must not be flipped just
    # because day-first is tried as an alternative.
    series = pd.Series(["01/02/2024", "03/04/2024"])  # Jan 2, Mar 4 if month-first
    parsed = parse_dates_robust(series)

    # Both orderings parse everything here, so month-first (the tiebreak
    # default) wins and dates are not flipped.
    assert parsed.iloc[0] == pd.Timestamp("2024-01-02")
    assert parsed.iloc[1] == pd.Timestamp("2024-03-04")


def test_forwards_extra_kwargs_like_format() -> None:
    series = pd.Series(["2024-01-15", "28/11/2015"])
    parsed = parse_dates_robust(series, format="mixed")

    assert parsed.notna().sum() == 2
