import pytest

from app.common.enums import DatasetDomain, Priority
from app.intelligence.insight.generators.correlation_insights_generator import CorrelationInsightsGenerator
from app.intelligence.insight.generators.kpi_insights_generator import KPIInsightsGenerator
from app.intelligence.insight.generators.trend_insights_generator import TrendInsightsGenerator
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import (
    CorrelationResult,
    DataIntelligenceReport,
    QualityReport,
    StatisticalSummary,
    TrendResult,
)
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import Insight
from app.models.kpi_recommendation import KPIRecommendation


def create_mock_profiles():
    dataset_profile = DatasetProfile(dataset_name="sales.csv", total_rows=100, total_columns=5, detected_domain=DatasetDomain.RETAIL)
    kpis = (
        KPIRecommendation(name="Total Sales Revenue", priority=Priority.CRITICAL, confidence=0.95, reason="Revenue metric.", formula="SUM(Sales)"),
    )
    business_profile = BusinessProfile(
        domain=DatasetDomain.RETAIL,
        confidence=0.9,
        business_context="Retail sales",
        executive_summary="Retail summary",
        primary_kpis=kpis,
    )
    quality = QualityReport(overall_score=95.0, completeness_score=95.0, uniqueness_score=100.0, validity_score=90.0, total_issues=1)
    stats = StatisticalSummary(total_rows=100, numeric_columns_count=3, categorical_columns_count=2, date_columns_count=0)
    correlations = (
        CorrelationResult(column_a="units", column_b="revenue", coefficient=0.92, correlation_type="strong_positive", confidence=0.9, reasoning="High correlation."),
    )
    trends = (
        TrendResult(time_column="date", metric_column="revenue", direction="increasing", slope=15.0, growth_rate_pct=30.0, confidence=0.85, reasoning="30% growth."),
    )
    intel_report = DataIntelligenceReport(
        quality_report=quality,
        statistical_summary=stats,
        correlations=correlations,
        trends=trends,
        domain=DatasetDomain.RETAIL,
    )
    return dataset_profile, business_profile, intel_report


def test_kpi_insights_generator() -> None:
    generator = KPIInsightsGenerator()
    dataset_profile, business_profile, intel_report = create_mock_profiles()

    results = generator.generate(dataset_profile, business_profile, intel_report)
    assert isinstance(results, tuple)
    assert len(results) == 1
    insight = results[0]
    assert isinstance(insight, Insight)
    assert insight.category == "KPI"
    assert insight.severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
    assert insight.recommendation is not None
    assert len(insight.supporting_evidence) > 0


def test_trend_insights_generator() -> None:
    generator = TrendInsightsGenerator()
    dataset_profile, business_profile, intel_report = create_mock_profiles()

    results = generator.generate(dataset_profile, business_profile, intel_report)
    assert isinstance(results, tuple)
    assert len(results) == 1
    insight = results[0]
    assert isinstance(insight, Insight)
    assert insight.category == "TREND"
    assert "Growth" in insight.title or "Upward" in insight.title
    assert insight.confidence == 0.85


def test_correlation_insights_generator() -> None:
    generator = CorrelationInsightsGenerator()
    dataset_profile, business_profile, intel_report = create_mock_profiles()

    results = generator.generate(dataset_profile, business_profile, intel_report)
    assert isinstance(results, tuple)
    assert len(results) == 1
    insight = results[0]
    assert isinstance(insight, Insight)
    assert insight.category == "CORRELATION"
    assert "Driver" in insight.title or "Positive" in insight.title
