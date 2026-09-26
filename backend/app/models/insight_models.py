from dataclasses import dataclass, field
from typing import Optional

from app.common.enums import DatasetDomain, Priority


@dataclass(slots=True, frozen=True)
class Recommendation:
    """
    Immutable recommendation detailing an actionable business step.
    """

    action: str
    target_area: str
    expected_impact: str
    priority: Priority = Priority.MEDIUM


@dataclass(slots=True, frozen=True)
class Insight:
    """
    Immutable business insight synthesized from intelligence findings.
    """

    title: str
    description: str
    category: str  # 'KPI', 'TREND', 'CORRELATION', 'ANOMALY', 'BUSINESS_RULE', 'OPPORTUNITY'
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    priority: Priority
    confidence: float
    business_impact: str
    recommendation: Recommendation
    supporting_evidence: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class ExecutiveSummary:
    """
    Immutable executive narrative summarizing dataset overview, quality, findings, risks, and actions.
    """

    dataset_name: str
    domain: DatasetDomain
    overview: str
    data_quality_summary: str
    major_findings: tuple[str, ...] = field(default_factory=tuple)
    top_risks: tuple[str, ...] = field(default_factory=tuple)
    key_opportunities: tuple[str, ...] = field(default_factory=tuple)
    recommended_actions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class InsightReport:
    """
    Unified immutable report containing executive narrative and prioritized insights.
    """

    executive_summary: ExecutiveSummary
    insights: tuple[Insight, ...] = field(default_factory=tuple)
    kpi_insights: tuple[Insight, ...] = field(default_factory=tuple)
    trend_insights: tuple[Insight, ...] = field(default_factory=tuple)
    correlation_insights: tuple[Insight, ...] = field(default_factory=tuple)
    anomaly_insights: tuple[Insight, ...] = field(default_factory=tuple)
    business_rule_insights: tuple[Insight, ...] = field(default_factory=tuple)
    opportunity_insights: tuple[Insight, ...] = field(default_factory=tuple)
    domain: DatasetDomain = DatasetDomain.UNKNOWN
