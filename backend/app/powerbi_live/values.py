"""Turning what Analysis Services returns into a pandas DataFrame.

A DAX result reaches Python as .NET values. Numbers, text and booleans arrive as native Python
values, but BLANK arrives as ``System.DBNull`` (not ``None``) and dates as ``System.DateTime``
objects. Left alone the first becomes a stray object in a numeric column and the second never
parses, so both are converted here. Checks are duck-typed (class name, ``.Ticks``) so the logic can
be tested without a .NET runtime.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import pandas as pd

# .NET ticks (100 ns) between 0001-01-01 and the Unix epoch.
_EPOCH_TICKS = 621_355_968_000_000_000

INT, FLOAT, BOOL, DATETIME, TEXT = "int", "float", "bool", "datetime", "text"


def kind_for(tom_data_type: str) -> str:
    """Map a TOM column ``DataType`` name to how its values are converted."""
    return {
        "Int64": INT,
        "Double": FLOAT,
        "Decimal": FLOAT,
        "Boolean": BOOL,
        "DateTime": DATETIME,
    }.get(str(tom_data_type), TEXT)


def is_blank(value: Any) -> bool:
    return value is None or type(value).__name__ == "DBNull"


def column_name(raw: str, table: str) -> str:
    """``Sales Data[Amount]`` -> ``Amount``. A literal ``]`` in a name is doubled by DAX."""
    prefix = f"{table}["
    if raw.startswith(prefix) and raw.endswith("]"):
        return raw[len(prefix):-1].replace("]]", "]")
    return raw


def _ticks(value: Any) -> Optional[int]:
    if is_blank(value):
        return None
    if hasattr(value, "Ticks"):
        return int(value.Ticks)
    return int((pd.Timestamp(value).value // 100) + _EPOCH_TICKS)


def to_float(value: Any) -> float:
    """A float from a Python number, ``decimal.Decimal`` or a .NET ``System.Decimal``.

    pythonnet leaves ``System.Decimal`` as a .NET object that ``float()`` rejects. Its static
    ``ToDouble`` is used rather than ``str()``, whose output depends on the machine's culture
    (a decimal comma would turn 12.5 into 125 or an error).
    """
    try:
        return float(value)
    except TypeError:
        to_double = getattr(type(value), "ToDouble", None)
        if to_double is None:
            raise
        return float(to_double(value))


def convert_column(values: list[Any], kind: str) -> pd.Series:
    if kind == DATETIME:
        ticks = [_ticks(v) for v in values]
        nanoseconds = pd.Series([None if t is None else (t - _EPOCH_TICKS) * 100 for t in ticks], dtype="Int64")
        return pd.to_datetime(nanoseconds, unit="ns")

    cleaned = [None if is_blank(v) else v for v in values]
    has_blank = any(v is None for v in cleaned)
    if kind == INT:
        return pd.Series([None if v is None else int(v) for v in cleaned], dtype="float64" if has_blank else "int64")
    if kind == FLOAT:
        return pd.Series([None if v is None else to_float(v) for v in cleaned], dtype="float64")
    if kind == BOOL:
        return pd.Series([None if v is None else bool(v) for v in cleaned], dtype="object" if has_blank else "bool")
    return pd.Series([None if v is None else str(v) for v in cleaned], dtype="str")


def frame_from_rows(table: str, raw_names: list[str], kinds: list[str], rows: list[list[Any]]) -> pd.DataFrame:
    """A DataFrame with one typed column per result column and the table prefix removed from names."""
    names = [column_name(n, table) for n in raw_names]
    if len(set(names)) != len(names):
        raise ValueError("the table has columns whose names collide once the table prefix is removed")
    columns = list(zip(*rows)) if rows else [[] for _ in names]
    return pd.DataFrame({name: convert_column(list(col), kind) for name, kind, col in zip(names, kinds, columns)})
