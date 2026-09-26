import pytest

from app.common.enums import DatasetDomain, Priority
from app.intelligence.insight_engine import InsightEngine
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import (
    BusinessAnomaly,
    CorrelationResult,
    DataIntelligenceReport,
    QualityReport,
    StatisticalSummary,
    TrendResult,
)
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import ExecutiveSummary, Insight, InsightReport
from app.models.kpi_recommendation import KPIRecommendation


def test_insight_engine_orchestrator() -> None:
    engine = InsightEngine()

    dataset_profile = DatasetProfile(dataset_name="enterprise_sales.csv", total_rows=1000, total_columns=8, detected_domain=DatasetDomain.RETAIL)
    kpis = (
        KPIRecommendation(name="Total Revenue", priority=Priority.CRITICAL, confidence=0.95, reason="Core revenue", formula="SUM(Revenue)"),
    )
    business_profile = BusinessProfile(
        domain=DatasetDomain.RETAIL,
        confidence=0.92,
        business_context="Enterprise retail analytics",
        executive_summary="Executive context",
        primary_kpis=kpis,
    )
    intel_report = DataIntelligenceReport(
        quality_report=QualityReport(overall_score=88.0, completeness_score=85.0, uniqueness_score=95.0, validity_score=84.0, total_issues=3),
        statistical_summary=StatisticalSummary(total_rows=1000, numeric_columns_count=5, categorical_columns_count=3, date_columns_count=0),
        correlations=(CorrelationResult(column_a="units", column_b="revenue", coefficient=0.91, correlation_type="strong_positive", confidence=0.9, reasoning="r=0.91"),),
        trends=(TrendResult(time_column="date", metric_column="revenue", direction="increasing", slope=50.0, growth_rate_pct=40.0, confidence=0.85, reasoning="40% growth"),),
        business_anomalies=(BusinessAnomaly(anomaly_title="Negative Revenue", severity="CRITICAL", affected_entity="Order", metric_name="revenue", observed_value=-100.0, expected_value=0.0, deviation_pct=100.0, confidence=0.95, reasoning="Negative order revenue"),),
        overall_health_score=83.0,
        domain=DatasetDomain.RETAIL,
    )

    report = engine.generate(dataset_profile, business_profile, intel_report)

    assert isinstance(report, InsightReport)
    assert report.domain == DatasetDomain.RETAIL
    assert isinstance(report.executive_summary, ExecutiveSummary)
    assert isinstance(report.insights, tuple)
    assert len(report.insights) >= 5

    # Check prioritization: CRITICAL insights should come first
    first_insight = report.insights[0]
    assert isinstance(first_insight, Insight)
    assert first_insight.priority == Priority.CRITICAL

    # Verify categories
    assert len(report.kpi_insights) > 0
    assert len(report.trend_insights) > 0
    assert len(report.correlation_insights) > 0
    assert len(report.anomaly_insights) > 0
    assert len(report.business_rule_insights) > 0
