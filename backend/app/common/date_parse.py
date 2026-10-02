import warnings

import pandas as pd


def parse_dates_robust(series: pd.Series, **kwargs) -> pd.Series:
    """
    Parses date strings trying both month-first and day-first orderings and
    keeps whichever yields more valid timestamps.

    pd.to_datetime defaults to month-first (US) parsing. For a day-first
    dataset (e.g. "28/11/2015"), every date with day > 12 is unparseable
    under that default and becomes NaT -- silently dropping ~60% of a
    perfectly valid date column (every day-of-month past the 12th).
    """
    kwargs.pop("dayfirst", None)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        month_first = pd.to_datetime(series, errors="coerce", dayfirst=False, **kwargs)
        day_first = pd.to_datetime(series, errors="coerce", dayfirst=True, **kwargs)

    if day_first.notna().sum() > month_first.notna().sum():
        return day_first
    return month_first
