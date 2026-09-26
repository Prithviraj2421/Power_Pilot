"""Tolerant CSV decoding and parsing.

Real CSV files are not reliably UTF-8 with comma separators. Excel on Windows
writes cp1252 by default, "CSV UTF-8" adds a byte-order mark, "Unicode Text"
writes UTF-16, and Excel in a European locale writes semicolon-separated files
because the comma is the decimal separator there.

Demanding UTF-8 and commas rejects a large share of the files people actually
have. This module detects what it was given instead, and reports what it decided
so the choice is visible rather than silent.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.common.logger import get_logger

logger = get_logger("CsvReader")

# Byte-order marks, longest first so UTF-32 is not mistaken for UTF-16.
_BOMS: tuple[tuple[bytes, str], ...] = (
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xfe\xff", "utf-16-be"),
    (b"\xff\xfe", "utf-16-le"),
)

# Tried in order when there is no BOM. utf-8 first because it is correct far more
# often than not; cp1252 next because it is what Excel writes on Windows; latin-1
# last because it cannot fail -- every byte maps to a character -- which makes it
# a guaranteed fallback rather than a good guess.
_FALLBACK_ENCODINGS: tuple[str, ...] = ("utf-8", "cp1252", "latin-1")

_CANDIDATE_DELIMITERS = ",;\t|"


class CsvDecodeError(Exception):
    """Raised when the payload cannot be decoded as text by any known encoding."""


class CsvParseError(Exception):
    """Raised when decoded text cannot be parsed as tabular data."""


@dataclass(slots=True, frozen=True)
class CsvReadResult:
    """A parsed CSV plus the decisions that produced it."""

    dataframe: pd.DataFrame
    encoding: str
    delimiter: str
    had_bom: bool

    def describe(self) -> str:
        delimiter_name = {",": "comma", ";": "semicolon", "\t": "tab", "|": "pipe"}.get(
            self.delimiter, repr(self.delimiter)
        )
        return f"{self.encoding}{' with BOM' if self.had_bom else ''}, {delimiter_name}-separated"


def detect_encoding(payload: bytes) -> tuple[str, bool]:
    """Return the encoding to decode with, and whether a BOM was present.

    A BOM is authoritative, so it short-circuits the guesswork.
    """
    for bom, encoding in _BOMS:
        if payload.startswith(bom):
            return encoding, True

    for encoding in _FALLBACK_ENCODINGS:
        try:
            payload.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        return encoding, False

    raise CsvDecodeError(
        "The file could not be read as text in any supported encoding "
        "(UTF-8, UTF-16, UTF-32, Windows-1252 or Latin-1). "
        "If this is a spreadsheet, export it as CSV first."
    )


def decode(payload: bytes) -> tuple[str, str, bool]:
    """Decode the payload to text, returning (text, encoding, had_bom)."""
    encoding, had_bom = detect_encoding(payload)
    try:
        text = payload.decode(encoding)
    except UnicodeDecodeError as exc:  # pragma: no cover - detection already validated
        raise CsvDecodeError(f"Could not decode the file as {encoding}: {exc}") from exc

    # A BOM-less UTF-16 file decoded as cp1252/latin-1 becomes text riddled with
    # NUL characters. Catching that here gives a useful message instead of a
    # baffling parse failure downstream.
    if "\x00" in text[:4096]:
        raise CsvDecodeError(
            "The file contains null bytes, so it is not plain CSV text. "
            "If it is a spreadsheet or a UTF-16 export, re-save it as CSV UTF-8."
        )

    return text, encoding, had_bom


def detect_delimiter(text: str) -> str:
    """Sniff the field separator from the first few lines.

    Excel in a European locale writes semicolon-separated files, because the comma
    is the decimal separator there. csv.Sniffer is restricted to a candidate set so
    it cannot decide that some character inside the data is the separator.
    """
    sample = "\n".join(text.splitlines()[:20])
    if not sample.strip():
        return ","

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=_CANDIDATE_DELIMITERS)
    except csv.Error:
        return ","

    delimiter = dialect.delimiter

    # The sniffer can pick a delimiter that appears once in a header but yields a
    # single column overall. Prefer whichever candidate splits the header into the
    # most fields, with comma winning ties.
    header = text.splitlines()[0] if text.splitlines() else ""
    best = max(
        _CANDIDATE_DELIMITERS,
        key=lambda candidate: (header.count(candidate), candidate == ","),
    )
    if header.count(best) > header.count(delimiter):
        return best

    return delimiter


def read_csv(payload: bytes) -> CsvReadResult:
    """Decode and parse uploaded bytes into a DataFrame.

    Raises ``CsvDecodeError`` or ``CsvParseError`` with client-safe messages.
    """
    text, encoding, had_bom = decode(payload)
    delimiter = detect_delimiter(text)

    try:
        dataframe = pd.read_csv(io.StringIO(text), sep=delimiter)
    except pd.errors.EmptyDataError as exc:
        raise CsvParseError(
            "The file contains no parseable columns or headers."
        ) from exc
    except pd.errors.ParserError as exc:
        raise CsvParseError(
            "Malformed CSV syntax: the rows could not be parsed. "
            f"The separator was detected as {delimiter!r}; check for unclosed quotes "
            "or rows with differing column counts."
        ) from exc

    # A UTF-8 BOM decoded without utf-8-sig leaves a zero-width no-break space glued
    # to the first column name, producing a header like '﻿region' that never
    # matches anything downstream. utf-8-sig handles it, but other BOM encodings
    # can leave one behind too.
    dataframe.columns = [
        column.lstrip("﻿") if isinstance(column, str) else column
        for column in dataframe.columns
    ]

    if encoding != "utf-8" or delimiter != ",":
        logger.info(
            f"Parsed CSV as {encoding}{' with BOM' if had_bom else ''} "
            f"with delimiter {delimiter!r}"
        )

    return CsvReadResult(
        dataframe=dataframe,
        encoding=encoding,
        delimiter=delimiter,
        had_bom=had_bom,
    )
