"""Tests for tolerant CSV decoding and delimiter detection.

Real CSVs are not reliably UTF-8 with commas. Excel on Windows writes cp1252,
"CSV UTF-8" prepends a BOM, "Unicode Text" writes UTF-16, and a European locale
separates with semicolons. Every one of those was rejected with "Please upload a
UTF-8 encoded CSV" before this existed.
"""

from __future__ import annotations

import codecs

import pytest

from app.datasets.csv_reader import (
    CsvDecodeError,
    CsvParseError,
    detect_delimiter,
    detect_encoding,
    read_csv,
)

PLAIN = "region,revenue\nNorth,120\nSouth,90\n"
ACCENTED = "region,revenue,note\nNorth,120,café\nSüd,90,naïve\n"


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "encoding"),
    [
        ("plain utf-8", "utf-8"),
        ("Excel CSV UTF-8 (BOM)", "utf-8-sig"),
        ("Excel on Windows", "cp1252"),
        ("legacy latin-1", "latin-1"),
        ("Excel Unicode Text", "utf-16"),
    ],
)
def test_reads_every_common_spreadsheet_encoding(label: str, encoding: str) -> None:
    result = read_csv(ACCENTED.encode(encoding))

    assert list(result.dataframe.columns) == ["region", "revenue", "note"]
    assert len(result.dataframe) == 2


def test_accented_characters_survive_a_cp1252_round_trip() -> None:
    result = read_csv(ACCENTED.encode("cp1252"))

    notes = result.dataframe["note"].tolist()
    assert "café" in notes
    assert "naïve" in notes


def test_accented_characters_survive_a_utf16_round_trip() -> None:
    result = read_csv(ACCENTED.encode("utf-16"))

    assert "Süd" in result.dataframe["region"].tolist()


def test_a_bom_is_reported_and_stripped_from_the_first_column() -> None:
    """A BOM left in place produces a header like '\\ufeffregion' that matches nothing."""
    result = read_csv(PLAIN.encode("utf-8-sig"))

    assert result.had_bom is True
    assert result.dataframe.columns[0] == "region"
    assert not result.dataframe.columns[0].startswith("﻿")


def test_utf8_is_preferred_when_the_bytes_are_valid_utf8() -> None:
    encoding, had_bom = detect_encoding(ACCENTED.encode("utf-8"))

    assert encoding == "utf-8"
    assert had_bom is False


def test_bom_takes_priority_over_guessing() -> None:
    # Note: "utf-16-le"/"utf-16-be" do NOT emit a BOM; only "utf-16" does. The
    # marks are prepended explicitly here so the detection path is what is tested.
    assert detect_encoding(PLAIN.encode("utf-8-sig")) == ("utf-8-sig", True)
    assert detect_encoding(codecs.BOM_UTF16_LE + PLAIN.encode("utf-16-le")) == (
        "utf-16-le",
        True,
    )
    assert detect_encoding(codecs.BOM_UTF16_BE + PLAIN.encode("utf-16-be")) == (
        "utf-16-be",
        True,
    )
    assert detect_encoding(PLAIN.encode("utf-16")) == ("utf-16-le", True)


def test_bomless_utf16_is_rejected_rather_than_silently_mangled() -> None:
    """Without a BOM, UTF-16 bytes are valid UTF-8 full of NULs.

    Decoding them "successfully" would yield a header like 'r\\x00e\\x00g...' and a
    baffling downstream failure, so the null-byte guard stops it here.
    """
    with pytest.raises(CsvDecodeError, match="null bytes"):
        read_csv(PLAIN.encode("utf-16-le"))


def test_non_utf8_bytes_fall_back_to_cp1252() -> None:
    encoding, had_bom = detect_encoding(ACCENTED.encode("cp1252"))

    assert encoding == "cp1252"
    assert had_bom is False


def test_binary_content_is_rejected_with_a_useful_message() -> None:
    """A .csv that is really a spreadsheet should say so, not fail cryptically."""
    with pytest.raises(CsvDecodeError, match="null bytes"):
        read_csv(b"PK\x03\x04\x00\x00\x00\x00 this is actually an xlsx \x00\x00")


# ---------------------------------------------------------------------------
# Delimiters
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("delimiter", [",", ";", "\t", "|"])
def test_detects_each_supported_delimiter(delimiter: str) -> None:
    text = ACCENTED.replace(",", delimiter)
    result = read_csv(text.encode("utf-8"))

    assert result.delimiter == delimiter
    assert list(result.dataframe.columns) == ["region", "revenue", "note"]
    assert len(result.dataframe) == 2


def test_european_excel_semicolon_file_parses_into_columns() -> None:
    """The failure mode this prevents is one column containing the whole row."""
    result = read_csv("region;revenue\nNorth;120\nSouth;90\n".encode("cp1252"))

    assert result.delimiter == ";"
    assert len(result.dataframe.columns) == 2
    assert result.dataframe["revenue"].tolist() == [120, 90]


def test_commas_inside_quoted_fields_do_not_split_columns() -> None:
    text = 'region,note\nNorth,"Berlin, Germany"\n'
    result = read_csv(text.encode("utf-8"))

    assert list(result.dataframe.columns) == ["region", "note"]
    assert result.dataframe["note"].iloc[0] == "Berlin, Germany"


def test_delimiter_detection_defaults_to_comma_on_a_single_column() -> None:
    assert detect_delimiter("region\nNorth\nSouth\n") == ","


def test_delimiter_detection_handles_empty_text() -> None:
    assert detect_delimiter("") == ","


# ---------------------------------------------------------------------------
# Parse failures
# ---------------------------------------------------------------------------


def test_empty_payload_reports_no_parseable_columns() -> None:
    with pytest.raises(CsvParseError, match="no parseable columns"):
        read_csv(b"\n")


def test_ragged_rows_report_the_detected_separator() -> None:
    ragged = b'a,b\n1,2\n"unclosed,3,4,5,6\n7,8,9,10,11\n'
    try:
        read_csv(ragged)
    except CsvParseError as exc:
        assert "separator was detected" in str(exc)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def test_describe_is_human_readable() -> None:
    assert read_csv(PLAIN.encode("utf-8")).describe() == "utf-8, comma-separated"
    assert "semicolon-separated" in read_csv(b"a;b\n1;2\n").describe()
    assert "with BOM" in read_csv(PLAIN.encode("utf-8-sig")).describe()


def test_detection_is_deterministic_across_repeated_reads() -> None:
    """A stored dataset is re-parsed on every cache miss; it must not drift."""
    payload = ACCENTED.encode("cp1252")
    first = read_csv(payload)
    second = read_csv(payload)

    assert first.encoding == second.encoding
    assert first.delimiter == second.delimiter
    assert first.dataframe.equals(second.dataframe)
