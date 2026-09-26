from dataclasses import dataclass, field
from typing import Any

from app.common.enums import DatasetDomain
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation


@dataclass(slots=True, frozen=True)
class BusinessProfile:
    """
    Represents the executive business understanding of a dataset.

    Synthesizes technical metadata, detected semantic entities, and domain
    classification into actionable BI recommendations, KPIs, questions, charts,
    and dashboard blueprints.
    """

    # ── Core Domain Information ───────────────────────────────────
    domain: DatasetDomain
    confidence: float
    business_context: str
    executive_summary: str

    # ── Business Performance Metrics & KPIs ─────────────────────────
    primary_kpis: tuple[KPIRecommendation, ...] = field(default_factory=tuple)
    secondary_kpis: tuple[KPIRecommendation, ...] = field(default_factory=tuple)

    # ── Dimensions & Measures ─────────────────────────────────────
    dimensions: tuple[str, ...] = field(default_factory=tuple)
    measures: tuple[str, ...] = field(default_factory=tuple)

    # ── Executive Questions & Insights ─────────────────────────────
    business_questions: tuple[str, ...] = field(default_factory=tuple)
    recommended_insights: tuple[str, ...] = field(default_factory=tuple)

    # ── Dashboard & Visualization Recommendations ──────────────────
    suggested_charts: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    suggested_dashboard_layout: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    suggested_filters: tuple[str, ...] = field(default_factory=tuple)
    time_intelligence: tuple[str, ...] = field(default_factory=tuple)

    # ── Data Governance & Quality ─────────────────────────────────
    relationships: tuple[str, ...] = field(default_factory=tuple)
    data_quality_notes: tuple[str, ...] = field(default_factory=tuple)

    # ── Entity & Metadata Attachments ─────────────────────────────
    entities: tuple[DetectedEntity, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)