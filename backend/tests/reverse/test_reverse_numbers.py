"""Reading displayed numbers, and the precision they show."""

from __future__ import annotations

import math

import pytest

from app.reverse.numbers import FormatInfo, interpret_format, is_date_format, parse_number, show


@pytest.mark.parametrize(
    ("text", "value", "decimals", "unit"),
    [
        ("1234", 1234, 0, "number"),
        ("1,234", 1234, 0, "number"),
        ("1,234.56", 1234.56, 2, "number"),
        ("12.5", 12.5, 1, "number"),
        ("-1,200", -1200, 0, "number"),
        ("(1,200)", -1200, 0, "number"),
        ("(1,200.50)", -1200.5, 2, "number"),
        ("1,200-", -1200, 0, "number"),
        ("−1,200", -1200, 0, "number"),  # unicode minus
        ("+7", 7, 0, "number"),
        ("12.5%", 0.125, 1, "percent"),
        ("-3%", -0.03, 0, "percent"),
        ("(4.25%)", -0.0425, 2, "percent"),
        ("₹1,24,500", 124500, 0, "currency"),  # Indian grouping
        ("₹ 12,34,567.50", 1234567.5, 2, "currency"),
        ("Rs. 1,24,500", 124500, 0, "currency"),
        ("INR 5,000", 5000, 0, "currency"),
        ("$1,234.50", 1234.5, 2, "currency"),
        ("$-1,200", -1200, 0, "currency"),
        ("€ 1.234,56", 1234.56, 2, "currency"),  # European: dot groups, comma decimal
        ("1.234,56", 1234.56, 2, "number"),
        ("12,5", 12.5, 1, "number"),
        ("1.234.567", 1234567, 0, "number"),
        ("1 234 567", 1234567, 0, "number"),
        ("1 234,5", 1234.5, 1, "number"),
        ("1.2M", 1_200_000, 1, "number"),
        ("12 K", 12_000, 0, "number"),
        ("3.45B", 3_450_000_000, 2, "number"),
        ("2.5 Cr", 25_000_000, 1, "number"),
        ("4 lakh", 400_000, 0, "number"),
        ("$1.2M", 1_200_000, 1, "currency"),
        (1234, 1234, 0, "number"),
        (12.375, 12.375, 3, "number"),
    ],
)
def test_value_decimals_and_unit(text, value, decimals, unit) -> None:
    parsed = parse_number(text)
    assert parsed is not None, text
    assert math.isclose(parsed.value, value, rel_tol=1e-12), (text, parsed)
    assert (parsed.decimals, parsed.unit) == (decimals, unit), (text, parsed)


@pytest.mark.parametrize(
    "text",
    ["", "  ", "-", "—", "n/a", "N/A", "#DIV/0!", "Region", "Q3", "Jan 2024", "12 units", "1,2,3", "1..2", "abc1", "%", "$", None, True, "1.2.3"],
)
def test_labels_and_blank_markers_are_not_numbers(text) -> None:
    assert parse_number(text) is None


def test_tolerance_is_half_a_unit_in_the_last_shown_place() -> None:
    assert parse_number("1,234").tolerance == pytest.approx(0.5)
    assert parse_number("1,234.50").tolerance == pytest.approx(0.005)
    assert parse_number("12.5%").tolerance == pytest.approx(0.0005)  # 12.45% .. 12.55%, in fractions
    assert parse_number("1.2M").tolerance == pytest.approx(50_000)
    assert parse_number("3 Cr").tolerance == pytest.approx(5_000_000)


def test_a_shown_value_matches_formulas_that_round_to_it_and_no_others() -> None:
    shown = parse_number("1.2M")
    assert abs(1_234_567 - shown.value) <= shown.tolerance
    assert abs(1_260_000 - shown.value) > shown.tolerance


# --- Excel number formats ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fmt", "value", "expected"),
    [
        ("General", 12.0, FormatInfo(0, "number", 1.0)),
        ("General", 12.375, FormatInfo(3, "number", 1.0)),
        ("0", 3.7, FormatInfo(0, "number", 1.0)),
        ("#,##0", 1234.5, FormatInfo(0, "number", 1.0)),
        ("#,##0.00", 1234.5, FormatInfo(2, "number", 1.0)),
        ("0.0%", 0.125, FormatInfo(1, "percent", 0.01)),
        ("0%", 0.5, FormatInfo(0, "percent", 0.01)),
        ('"$"#,##0.00', 5.0, FormatInfo(2, "currency", 1.0)),
        ("[$₹-4009] #,##0", 5.0, FormatInfo(0, "currency", 1.0)),
        ("#,##0,", 1_500_000, FormatInfo(0, "number", 1000.0)),  # thousands scaling
        ('0.0,,"M"', 1_500_000, FormatInfo(1, "number", 1e6)),
        ("#,##0.00;[Red](#,##0.00)", -5.0, FormatInfo(2, "number", 1.0)),
        ("#,##0;(#,##0)", 5.0, FormatInfo(0, "number", 1.0)),
    ],
)
def test_excel_formats(fmt, value, expected) -> None:
    assert interpret_format(fmt, value) == expected


@pytest.mark.parametrize("fmt", ["yyyy-mm-dd", "d/m/yyyy", "mmm yy", "hh:mm:ss", "dd-mmm"])
def test_date_formats_are_recognised(fmt) -> None:
    assert is_date_format(fmt)


@pytest.mark.parametrize("fmt", ["General", "0.00", "#,##0", "0.0%", '0.0,,"M"', "[Red]0.00"])
def test_number_formats_are_not_dates(fmt) -> None:
    assert not is_date_format(fmt)


def test_show_renders_what_excel_would_show() -> None:
    assert show(1234.5, FormatInfo(2, "number", 1.0, grouped=True)) == "1,234.50"
    assert show(1234.5, FormatInfo(2, "number", 1.0)) == "1234.50"
    assert show(0.125, FormatInfo(1, "percent", 0.01)) == "12.5%"
    assert show(-5.0, FormatInfo(0, "currency", 1.0)) == "-$5"
    assert show(1_500_000, FormatInfo(1, "number", 1e6)) == "1.5M"
