from dataclasses import dataclass, field
from typing import Any

from app.common.enums import DatasetDomain
from app.models.column_profile import ColumnProfile


@dataclass
class DatasetProfile:
    """
    Represents the structural and semantic understanding of an uploaded dataset.

    Produced by Schema Analyzer, enriched by Entity Detector and Domain Classifier.
    """

    # ── Required Fields ─────────────────────────────────────────
    dataset_name: str
    total_rows: int
    total_columns: int

    # ── Optional Fields (with defaults) ─────────────────────────
    columns: list[ColumnProfile] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Domain Classification Fields (enriched by DomainClassifier) ──
    detected_domain: DatasetDomain = DatasetDomain.UNKNOWN
    domain_confidence: float = 0.0
    candidate_domains: list[Any] = field(default_factory=list)