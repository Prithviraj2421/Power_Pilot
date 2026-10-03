"""Metadata describing a registered dataset."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(slots=True, frozen=True)
class DatasetRecord:
    """A registered dataset's durable metadata.

    Row counts reflect both sides of Stage 1: ``original_rows`` is what was
    uploaded, ``total_rows`` is what survived cleaning. Keeping both means the
    "Original vs Cleaned" comparison never has to be back-computed by guesswork.
    """

    dataset_id: str
    filename: str
    stored_path: str
    size_bytes: int
    content_sha256: str
    original_rows: int
    total_rows: int
    total_columns: int
    detected_domain: str
    domain_confidence: float
    quality_grade: str
    quality_score: float
    quality_issues_count: int
    created_at: str
    last_accessed_at: str
    # How the upload was actually read. Worth surfacing: if a file came through as
    # cp1252 and some characters look wrong, or an Excel import picked the wrong
    # sheet, this is the first thing to check.
    source_encoding: str = "utf-8"
    source_delimiter: str = ","
    source_file_format: str = "csv"
    source_sheet: Optional[str] = None
    # Set when the data was read from a table of an open Power BI model rather than uploaded.
    powerbi_table: Optional[str] = None
    # Which frame KPIs are verified against: the cleaned one (uploads) or the data as read (live).
    verify_on: str = "cleaned"

    @property
    def is_live_model(self) -> bool:
        return self.powerbi_table is not None

    @property
    def source_format(self) -> str:
        """Human-readable description of how the upload was read."""
        if self.source_file_format in ("xlsx", "xlsm"):
            sheet = f", sheet '{self.source_sheet}'" if self.source_sheet else ""
            return f"{self.source_file_format}{sheet}"
        if self.source_file_format == "json":
            return "json"

        delimiter_name = {",": "comma", ";": "semicolon", "\t": "tab", "|": "pipe"}.get(
            self.source_delimiter, repr(self.source_delimiter)
        )
        return f"{self.source_encoding}, {delimiter_name}-separated"

    @property
    def read_with_defaults(self) -> bool:
        """True when nothing about how the file was read is worth mentioning.

        A plain UTF-8 comma-separated CSV is the unremarkable case. Any other
        format, encoding, delimiter or sheet choice is something the user may want
        to know about if the data looks wrong.
        """
        return (
            self.source_file_format == "csv"
            and self.source_encoding == "utf-8"
            and self.source_delimiter == ","
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable view for API responses.

        ``stored_path`` is intentionally omitted: it is a server filesystem
        location and has no business reaching a client.
        """
        return {
            "dataset_id": self.dataset_id,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "content_sha256": self.content_sha256,
            "original_rows": self.original_rows,
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "rows_removed_by_cleaning": self.original_rows - self.total_rows,
            "detected_domain": self.detected_domain,
            "domain_confidence": self.domain_confidence,
            "quality_grade": self.quality_grade,
            "quality_score": self.quality_score,
            "quality_issues_count": self.quality_issues_count,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "source_encoding": self.source_encoding,
            "source_delimiter": self.source_delimiter,
            "source_file_format": self.source_file_format,
            "source_sheet": self.source_sheet,
            "powerbi_table": self.powerbi_table,
            "source_format": self.source_format,
            "read_with_defaults": self.read_with_defaults,
        }
