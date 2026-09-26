"""Metadata describing a registered dataset."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
        }
