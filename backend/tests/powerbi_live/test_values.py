import datetime
from decimal import Decimal

import pandas as pd
import pytest

from app.powerbi_live.values import (
    BOOL, DATETIME, FLOAT, INT, TEXT, column_name, convert_column, frame_from_rows, is_blank, kind_for,
)

EPOCH_TICKS = 621_355_968_000_000_000


class DBNull:
    """Stands in for System.DBNull, which is recognised by its class name."""


class NetDecimal:
    """Stands in for System.Decimal under pythonnet: not convertible by float(), but has a static ToDouble."""

    def __init__(self, text: str) -> None:
        self._text = text

    @staticmethod
    def ToDouble(value: "NetDecimal") -> float:
        return float(value._text)

    def __str__(self) -> str:  # a locale-dependent ToString(): must never be what we parse
        return self._text.replace(".", ",")


class NetDateTime:
    """Stands in for System.DateTime, which exposes .Ticks."""

    def __init__(self, ts: str) -> None:
        self.Ticks = EPOCH_TICKS + pd.Timestamp(ts).value // 100


def test_blank_is_dbnull_or_none() -> None:
    assert is_blank(None) and is_blank(DBNull())
    assert not is_blank(0) and not is_blank("") and not is_blank(False), "falsy values are still values"


@pytest.mark.parametrize(
    ("tom_type", "kind"),
    [("Int64", INT), ("Double", FLOAT), ("Decimal", FLOAT), ("Boolean", BOOL), ("DateTime", DATETIME),
     ("String", TEXT), ("Variant", TEXT), ("Binary", TEXT)],
)
def test_tom_types_map_to_conversion_kinds(tom_type: str, kind: str) -> None:
    assert kind_for(tom_type) == kind


def test_result_column_names_lose_the_table_prefix() -> None:
    assert column_name("Sales Data[Amount]", "Sales Data") == "Amount"
    assert column_name("Sales Data[odd]]name]", "Sales Data") == "odd]name"
    assert column_name("Amount", "Sales Data") == "Amount", "an unprefixed name is left alone"
    assert column_name("Other[Amount]", "Sales Data") == "Other[Amount]"


def test_integers_stay_integers_until_a_blank_forces_floats() -> None:
    assert convert_column([1, 2, 3], INT).dtype == "int64"
    with_blank = convert_column([1, DBNull(), 3], INT)
    assert with_blank.dtype == "float64" and pd.isna(with_blank[1])


def test_decimals_become_floats_and_blank_becomes_nan() -> None:
    series = convert_column([Decimal("1.50"), DBNull(), Decimal("2.25")], FLOAT)
    assert series.dtype == "float64" and series[0] == 1.5 and pd.isna(series[1]) and series[2] == 2.25


def test_dbnull_never_leaks_into_a_numeric_column() -> None:
    series = convert_column([DBNull(), DBNull()], FLOAT)
    assert series.isna().all() and series.dtype == "float64"


def test_booleans_keep_their_type_and_blanks_are_kept_apart() -> None:
    assert convert_column([True, False], BOOL).dtype == "bool"
    mixed = convert_column([True, DBNull()], BOOL)
    assert mixed[0] is True and pd.isna(mixed[1])


def test_net_datetimes_become_timestamps_to_the_nanosecond_and_blank_becomes_nat() -> None:
    series = convert_column([NetDateTime("2024-03-05 14:30:15"), DBNull(), NetDateTime("1999-12-31")], DATETIME)

    assert series[0] == pd.Timestamp("2024-03-05 14:30:15")
    assert pd.isna(series[1])
    assert series[2] == pd.Timestamp("1999-12-31")
    assert str(series.dtype).startswith("datetime64")


def test_plain_python_datetimes_are_accepted_too() -> None:
    series = convert_column([datetime.datetime(2024, 1, 2, 3, 4, 5)], DATETIME)
    assert series[0] == pd.Timestamp("2024-01-02 03:04:05")


def test_text_is_text_and_blank_text_is_missing_not_the_word_none() -> None:
    series = convert_column(["East", DBNull(), 7], TEXT)
    assert series[0] == "East" and pd.isna(series[1]) and series[2] == "7"


def test_a_frame_is_built_with_clean_names_and_a_type_per_column() -> None:
    rows = [[1, "East", Decimal("9.5"), NetDateTime("2024-01-01"), True],
            [DBNull(), DBNull(), DBNull(), DBNull(), DBNull()]]
    frame = frame_from_rows(
        "Sales", ["Sales[Id]", "Sales[Region]", "Sales[Amount]", "Sales[When]", "Sales[Flag]"],
        [INT, TEXT, FLOAT, DATETIME, BOOL], rows,
    )

    assert list(frame.columns) == ["Id", "Region", "Amount", "When", "Flag"]
    assert frame["Amount"].iloc[0] == 9.5 and frame.isna().iloc[1].all()
    assert frame["When"].iloc[0] == pd.Timestamp("2024-01-01")


def test_an_empty_result_still_has_its_columns() -> None:
    frame = frame_from_rows("T", ["T[a]", "T[b]"], [INT, TEXT], [])
    assert list(frame.columns) == ["a", "b"] and len(frame) == 0


def test_names_that_collide_after_stripping_are_rejected_not_silently_merged() -> None:
    with pytest.raises(ValueError, match="collide"):
        frame_from_rows("T", ["T[a]", "a"], [INT, INT], [[1, 2]])


def test_net_decimals_are_converted_with_todouble_not_through_their_locale_dependent_text() -> None:
    series = convert_column([NetDecimal("12.5"), DBNull(), NetDecimal("0.0001")], FLOAT)

    assert series[0] == 12.5 and pd.isna(series[1]) and series[2] == 0.0001
    assert str(NetDecimal("12.5")) == "12,5", "the stand-in's text really is locale-formatted"
