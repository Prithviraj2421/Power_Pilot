"""Multi-format dataset ingestion.

Everything downstream of Stage 1 operates on a DataFrame and does not care where
it came from, so the CSV-only restriction lived entirely in the upload gate. That
made the most common real-world case -- someone with an .xlsx open in Excel --
impossible without a manual export step.

This module turns uploaded bytes into a DataFrame for each supported format and
reports how it did so, since "which sheet did it read?" is exactly the question a
user asks when an Excel import looks wrong.

Deliberately not supported: legacy .xls (needs xlrd, a dead format) and Parquet
(needs pyarrow, a heavy dependency for a format nobody exports from a
spreadsheet). Both raise a clear message naming the alternative.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from app.common.logger import get_logger
from app.datasets.csv_reader import CsvDecodeError, CsvParseError, decode, read_csv

logger = get_logger("DatasetReader")

CSV_EXTENSIONS = frozenset({".csv", ".tsv", ".txt"})
EXCEL_EXTENSIONS = frozenset({".xlsx", ".xlsm"})
JSON_EXTENSIONS = frozenset({".json"})

SUPPORTED_EXTENSIONS = CSV_EXTENSIONS | EXCEL_EXTENSIONS | JSON_EXTENSIONS

# Formats a user might plausibly try, with the reason they are refused. Naming the
# fix is more useful than a generic "unsupported file type".
_KNOWN_UNSUPPORTED: dict[str, str] = {
    ".xls": (
        "Legacy .xls files are not supported. Open the file in Excel and save it "
        "as .xlsx or CSV."
    ),
    ".parquet": "Parquet files are not supported yet. Export the data as CSV or .xlsx.",
    ".ods": (
        "OpenDocument .ods files are not supported. Save the file as .xlsx or CSV."
    ),
    ".pdf": "PDFs are not datasets. Export the underlying table as CSV or .xlsx.",
    ".doc": "Word documents are not datasets. Export the table as CSV or .xlsx.",
    ".docx": "Word documents are not datasets. Export the table as CSV or .xlsx.",
}


class UnsupportedFormatError(Exception):
    """Raised when the file extension is not one this application can read."""


class DatasetReadError(Exception):
    """Raised when a supported format could not be turned into a table."""


@dataclass(slots=True, frozen=True)
class DatasetReadResult:
    """A parsed dataset plus how it was read."""

    dataframe: pd.DataFrame
    file_format: str
    encoding: str = "n/a"
    delimiter: str = "n/a"
    sheet_name: Optional[str] = None
    had_bom: bool = False

    def describe(self) -> str:
        """Human-readable summary, e.g. "xlsx, sheet 'Q3 Sales'"."""
        if self.file_format in ("xlsx", "xlsm"):
            sheet = f", sheet '{self.sheet_name}'" if self.sheet_name else ""
            return f"{self.file_format}{sheet}"
        if self.file_format == "json":
            return "json"

        delimiter_name = {",": "comma", ";": "semicolon", "\t": "tab", "|": "pipe"}.get(
            self.delimiter, repr(self.delimiter)
        )
        return f"{self.encoding}, {delimiter_name}-separated"


def extension_of(filename: str) -> str:
    return Path(filename).suffix.lower()


def is_supported(filename: str) -> bool:
    return extension_of(filename) in SUPPORTED_EXTENSIONS


def _supported_list() -> str:
    return ", ".join(sorted(SUPPORTED_EXTENSIONS))


def read_excel(payload: bytes, sheet: Optional[str] = None) -> DatasetReadResult:
    """Read the first sheet that contains data, or a named one.

    Workbooks routinely carry cover sheets, notes tabs and empty scratch sheets, so
    taking sheet 0 unconditionally often yields an empty or meaningless table. The
    chosen sheet is reported so a wrong guess is visible rather than mysterious.
    """
    try:
        workbook = pd.ExcelFile(io.BytesIO(payload), engine="openpyxl")
    except Exception as exc:
        raise DatasetReadError(
            "Could not open the workbook. It may be corrupt, password protected, "
            "or not a real .xlsx file."
        ) from exc

    sheet_names = list(workbook.sheet_names)
    if not sheet_names:
        raise DatasetReadError("The workbook contains no sheets.")

    if sheet is not None:
        if sheet not in sheet_names:
            raise DatasetReadError(
                f"Sheet '{sheet}' is not in this workbook. Available sheets: "
                f"{', '.join(sheet_names)}."
            )
        candidates = [sheet]
    else:
        candidates = sheet_names

    last_error: Optional[Exception] = None
    for name in candidates:
        try:
            frame = workbook.parse(name)
        except Exception as exc:  # a single malformed sheet should not sink the file
            last_error = exc
            continue
        if not frame.empty and len(frame.columns) > 0:
            if name != sheet_names[0]:
                logger.info(
                    f"Sheet '{sheet_names[0]}' held no data; read '{name}' instead"
                )
            return DatasetReadResult(
                dataframe=frame,
                file_format="xlsx",
                sheet_name=name,
            )

    if last_error is not None:
        raise DatasetReadError(
            f"No readable sheet found in the workbook: {last_error}"
        ) from last_error
    raise DatasetReadError(
        f"Every sheet in the workbook is empty (checked: {', '.join(candidates)})."
    )


def read_json(payload: bytes) -> DatasetReadResult:
    """Read JSON in the shapes an API or export actually produces.

    Handles a top-level array of objects, a wrapper object with a single array
    under a key such as "data"/"records"/"rows"/"results", and newline-delimited
    JSON.
    """
    try:
        text, _encoding, _had_bom = decode(payload)
    except CsvDecodeError as exc:
        raise DatasetReadError(str(exc)) from exc

    stripped = text.strip()
    if not stripped:
        raise DatasetReadError("The JSON file is empty.")

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        # Newline-delimited JSON is several documents in one file, so a whole-file
        # parse fails with "Extra data". Sniffing for it up front is unreliable --
        # well-formed NDJSON still ends with '}' like a plain object -- so it is
        # tried here, where standard JSON has already been ruled out.
        try:
            frame = pd.read_json(io.StringIO(stripped), lines=True)
        except ValueError:
            raise DatasetReadError(
                f"The file is not valid JSON: {exc.msg} (line {exc.lineno})."
            ) from exc

        if frame.empty or len(frame.columns) == 0:
            raise DatasetReadError("The JSON file contains no records.") from exc
        return DatasetReadResult(dataframe=frame, file_format="json")

    records: object = parsed
    if isinstance(parsed, dict):
        array_keys = [key for key, value in parsed.items() if isinstance(value, list)]
        if len(array_keys) == 1:
            records = parsed[array_keys[0]]
        elif not array_keys:
            # A single object is one row.
            records = [parsed]
        else:
            preferred = next(
                (k for k in ("data", "records", "rows", "results", "items") if k in array_keys),
                None,
            )
            if preferred is None:
                raise DatasetReadError(
                    "The JSON object holds several arrays "
                    f"({', '.join(sorted(array_keys))}), so the table to load is "
                    "ambiguous. Provide a top-level array of records instead."
                )
            records = parsed[preferred]

    if not isinstance(records, list):
        raise DatasetReadError(
            "Expected a JSON array of records, or an object containing one."
        )
    if not records:
        raise DatasetReadError("The JSON file contains no records.")

    try:
        frame = pd.json_normalize(records)
    except Exception as exc:
        raise DatasetReadError(f"Could not convert the JSON records to a table: {exc}") from exc

    return DatasetReadResult(dataframe=frame, file_format="json")


def read_dataset(
    payload: bytes, filename: str, sheet: Optional[str] = None
) -> DatasetReadResult:
    """Turn uploaded bytes into a DataFrame, dispatching on the file extension.

    Raises ``UnsupportedFormatError`` or ``DatasetReadError`` with client-safe
    messages.
    """
    extension = extension_of(filename)

    if extension in _KNOWN_UNSUPPORTED:
        raise UnsupportedFormatError(_KNOWN_UNSUPPORTED[extension])

    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"Unsupported file type '{extension or filename}'. "
            f"Supported formats: {_supported_list()}."
        )

    if extension in EXCEL_EXTENSIONS:
        return read_excel(payload, sheet=sheet)

    if extension in JSON_EXTENSIONS:
        return read_json(payload)

    # Text formats. Encoding and delimiter are detected, so a .txt or .tsv with
    # any of the supported separators is read correctly.
    try:
        parsed = read_csv(payload)
    except (CsvDecodeError, CsvParseError) as exc:
        raise DatasetReadError(str(exc)) from exc

    return DatasetReadResult(
        dataframe=parsed.dataframe,
        file_format=extension.lstrip("."),
        encoding=parsed.encoding,
        delimiter=parsed.delimiter,
        had_bom=parsed.had_bom,
    )
