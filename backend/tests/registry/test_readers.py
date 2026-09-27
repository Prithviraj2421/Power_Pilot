"""Tests for multi-format dataset ingestion.

Everything after Stage 1 operates on a DataFrame, so the CSV-only restriction was
purely an upload gate. These cover the formats people actually have: workbooks
straight out of Excel, JSON from an API, and tab-separated exports.
"""

from __future__ import annotations

import io
import json

import pandas as pd
import pytest

from app.datasets.readers import (
    SUPPORTED_EXTENSIONS,
    DatasetReadError,
    UnsupportedFormatError,
    is_supported,
    read_dataset,
    read_excel,
    read_json,
)

FRAME = pd.DataFrame(
    {
        "region": ["North", "South", "East"],
        "revenue": [120.5, 90.0, 240.25],
        "units": [3, 2, 7],
    }
)


def _workbook(**sheets: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------


def test_reads_a_single_sheet_workbook() -> None:
    result = read_dataset(_workbook(Sales=FRAME), "report.xlsx")

    assert result.file_format == "xlsx"
    assert result.sheet_name == "Sales"
    assert list(result.dataframe.columns) == ["region", "revenue", "units"]
    assert len(result.dataframe) == 3


def test_excel_values_survive_intact() -> None:
    result = read_dataset(_workbook(Sales=FRAME), "report.xlsx")

    assert result.dataframe["revenue"].tolist() == [120.5, 90.0, 240.25]
    assert result.dataframe["region"].tolist() == ["North", "South", "East"]


def test_xlsm_macro_workbooks_are_accepted() -> None:
    result = read_dataset(_workbook(Data=FRAME), "macro_report.xlsm")
    assert result.dataframe.equals(FRAME)


def test_skips_a_leading_empty_sheet() -> None:
    """Workbooks routinely open with a cover or notes tab holding no data."""
    payload = _workbook(Cover=pd.DataFrame(), Sales=FRAME)

    result = read_dataset(payload, "report.xlsx")

    assert result.sheet_name == "Sales"
    assert len(result.dataframe) == 3


def test_a_named_sheet_can_be_requested() -> None:
    payload = _workbook(Q1=FRAME, Q2=FRAME.assign(revenue=[1.0, 2.0, 3.0]))

    result = read_dataset(payload, "report.xlsx", sheet="Q2")

    assert result.sheet_name == "Q2"
    assert result.dataframe["revenue"].tolist() == [1.0, 2.0, 3.0]


def test_requesting_a_missing_sheet_lists_what_is_available() -> None:
    payload = _workbook(Q1=FRAME, Q2=FRAME)

    with pytest.raises(DatasetReadError, match="Available sheets: Q1, Q2"):
        read_dataset(payload, "report.xlsx", sheet="Q3")


def test_a_fully_empty_workbook_is_rejected() -> None:
    with pytest.raises(DatasetReadError, match="empty"):
        read_dataset(_workbook(Cover=pd.DataFrame()), "empty.xlsx")


def test_a_corrupt_workbook_reports_clearly() -> None:
    with pytest.raises(DatasetReadError, match="corrupt, password protected"):
        read_excel(b"this is definitely not a workbook")


def test_describe_names_the_sheet() -> None:
    result = read_dataset(_workbook(Sales=FRAME), "report.xlsx")
    assert result.describe() == "xlsx, sheet 'Sales'"


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def test_reads_a_top_level_array_of_records() -> None:
    payload = json.dumps(FRAME.to_dict(orient="records")).encode("utf-8")

    result = read_dataset(payload, "data.json")

    assert result.file_format == "json"
    assert list(result.dataframe.columns) == ["region", "revenue", "units"]
    assert len(result.dataframe) == 3


def test_reads_records_wrapped_in_a_single_key() -> None:
    """The shape most APIs return."""
    payload = json.dumps({"data": FRAME.to_dict(orient="records")}).encode("utf-8")

    result = read_dataset(payload, "api_response.json")
    assert len(result.dataframe) == 3


@pytest.mark.parametrize("key", ["data", "records", "rows", "results", "items"])
def test_prefers_a_conventional_key_when_several_arrays_exist(key: str) -> None:
    payload = json.dumps(
        {key: FRAME.to_dict(orient="records"), "warnings": ["a", "b"]}
    ).encode("utf-8")

    result = read_dataset(payload, "api_response.json")
    assert len(result.dataframe) == 3


def test_ambiguous_multi_array_json_is_refused_rather_than_guessed() -> None:
    payload = json.dumps({"alpha": [{"a": 1}], "beta": [{"b": 2}]}).encode("utf-8")

    with pytest.raises(DatasetReadError, match="ambiguous"):
        read_dataset(payload, "ambiguous.json")


def test_a_single_object_becomes_one_row() -> None:
    result = read_dataset(b'{"region": "North", "revenue": 120}', "single.json")
    assert len(result.dataframe) == 1


def test_newline_delimited_json_is_read() -> None:
    lines = "\n".join(json.dumps(row) for row in FRAME.to_dict(orient="records"))
    result = read_dataset(lines.encode("utf-8"), "events.json")
    assert len(result.dataframe) == 3


def test_nested_json_is_flattened_into_columns() -> None:
    payload = json.dumps(
        [{"id": 1, "customer": {"name": "Ada", "city": "London"}}]
    ).encode("utf-8")

    result = read_dataset(payload, "nested.json")
    assert "customer.name" in result.dataframe.columns


def test_invalid_json_reports_the_line() -> None:
    with pytest.raises(DatasetReadError, match="not valid JSON"):
        read_dataset(b'{"a": 1,,}', "broken.json")


def test_empty_json_array_is_rejected() -> None:
    with pytest.raises(DatasetReadError, match="no records"):
        read_dataset(b"[]", "empty.json")


def test_empty_json_file_is_rejected() -> None:
    with pytest.raises(DatasetReadError, match="empty"):
        read_json(b"   ")


# ---------------------------------------------------------------------------
# Text formats
# ---------------------------------------------------------------------------


def test_tsv_files_are_read_as_tab_separated() -> None:
    payload = FRAME.to_csv(index=False, sep="\t").encode("utf-8")

    result = read_dataset(payload, "export.tsv")

    assert result.file_format == "tsv"
    assert result.delimiter == "\t"
    assert len(result.dataframe.columns) == 3


def test_txt_files_are_read_with_delimiter_detection() -> None:
    payload = FRAME.to_csv(index=False, sep=";").encode("utf-8")

    result = read_dataset(payload, "export.txt")

    assert result.file_format == "txt"
    assert result.delimiter == ";"


def test_csv_still_reports_encoding_and_delimiter() -> None:
    result = read_dataset(FRAME.to_csv(index=False).encode("utf-8"), "data.csv")

    assert result.file_format == "csv"
    assert result.describe() == "utf-8, comma-separated"


# ---------------------------------------------------------------------------
# Format gating
# ---------------------------------------------------------------------------


def test_supported_extensions_are_recognized() -> None:
    for extension in SUPPORTED_EXTENSIONS:
        assert is_supported(f"dataset{extension}")


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("legacy.xls", "save it as .xlsx or CSV"),
        ("data.parquet", "Export the data as CSV"),
        ("sheet.ods", "Save the file as .xlsx or CSV"),
        ("report.pdf", "Export the underlying table"),
        ("notes.docx", "Export the table"),
    ],
)
def test_known_unsupported_formats_name_the_fix(filename: str, expected: str) -> None:
    """Refusals should be actionable rather than a flat "unsupported"."""
    with pytest.raises(UnsupportedFormatError, match=expected):
        read_dataset(b"irrelevant", filename)


def test_unknown_extension_lists_the_supported_set() -> None:
    with pytest.raises(UnsupportedFormatError, match="Supported formats"):
        read_dataset(b"irrelevant", "mystery.dat")


def test_extension_matching_is_case_insensitive() -> None:
    result = read_dataset(_workbook(Sales=FRAME), "REPORT.XLSX")
    assert result.file_format == "xlsx"


def test_a_cover_sheet_with_one_note_row_is_not_mistaken_for_data() -> None:
    """Found with a real workbook: a "Read Me" tab holding a single note row is
    technically non-empty, so "first sheet with data" analyzed a 1x1 table while
    the real 900-row sheet sat next to it."""
    payload = _workbook(
        **{
            "Read Me": pd.DataFrame({"Notes": ["Confidential - HR analytics extract"]}),
            "Employees": FRAME,
        }
    )

    result = read_dataset(payload, "hr.xlsx")

    assert result.sheet_name == "Employees"
    assert len(result.dataframe) == 3


def test_the_largest_tabular_sheet_wins() -> None:
    small = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    large = pd.DataFrame({"a": range(50), "b": range(50), "c": range(50)})

    result = read_dataset(_workbook(Small=small, Large=large), "book.xlsx")

    assert result.sheet_name == "Large"


def test_a_named_sheet_still_overrides_the_ranking() -> None:
    """An explicit choice must beat the heuristic."""
    payload = _workbook(Summary=pd.DataFrame({"note": ["x"]}), Detail=FRAME)

    result = read_dataset(payload, "book.xlsx", sheet="Summary")

    assert result.sheet_name == "Summary"


def test_a_workbook_of_only_narrow_sheets_still_reads_the_biggest() -> None:
    """With nothing tabular, it should still return something rather than fail."""
    payload = _workbook(
        One=pd.DataFrame({"note": ["a"]}), Two=pd.DataFrame({"note": ["a", "b", "c"]})
    )

    result = read_dataset(payload, "notes.xlsx")

    assert result.sheet_name == "Two"
