from dataclasses import dataclass, field
from typing import Any

from app.common.enums import PhysicalType
from app.common.enums import SemanticType


@dataclass
class ColumnProfile:
    """
    Represents the complete profile of a single dataset column.

    Produced by the Schema Analyzer and enriched by later pipeline
    modules (Entity Detector, Domain Classifier, etc.).

    Fields are ordered with required fields first, then optional
    fields with defaults, per Python dataclass requirements.
    """

    # ── Required Fields (no defaults) ──────────────────────────
    name: str
    physical_type: PhysicalType
    nullable: bool
    unique: bool
    identifier: bool
    missing_count: int
    unique_count: int

    # ── Optional Fields (with defaults) ────────────────────────
    semantic_type: SemanticType = SemanticType.UNKNOWN
    sample_values: list[Any] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)