import pytest

from app.common.enums import DatasetDomain, Priority
from app.intelligence.insight.generators.executive_summary_generator import ExecutiveSummaryGenerator
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
from app.models.insight_models import ExecutiveSummary
from app.models.kpi_recommendation import KPIRecommendation


def test_executive_summary_generator() -> None:
    generator = ExecutiveSummaryGenerator()

    dataset_profile = DatasetProfile(dataset_name="transactions.csv", total_rows=500, total_columns=6, detected_domain=DatasetDomain.RETAIL)
    kpis = (
        KPIRecommendation(name="Total Sales Volume", priority=Priority.CRITICAL, confidence=0.9, reason="Primary sales metric", formula="SUM(Sales)"),
    )
    business_profile = BusinessProfile(
        domain=DatasetDomain.RETAIL,
        confidence=0.95,
        business_context="Retail POS analytics",
        executive_summary="Executive context for retail POS data.",
        primary_kpis=kpis,
    )
    intel_report = DataIntelligenceReport(
        quality_report=QualityReport(overall_score=92.0, completeness_score=90.0, uniqueness_score=100.0, validity_score=86.0, total_issues=2),
        statistical_summary=StatisticalSummary(total_rows=500, numeric_columns_count=4, categorical_columns_count=2, date_columns_count=0),
        correlations=(CorrelationResult(column_a="units", column_b="sales", coefficient=0.95, correlation_type="strong_positive", confidence=0.9, reasoning="r=0.95"),),
        trends=(TrendResult(time_column="date", metric_column="sales", direction="increasing", slope=10.0, growth_rate_pct=25.0, confidence=0.85, reasoning="25% growth"),),
        business_anomalies=(BusinessAnomaly(anomaly_title="Negative Pricing", severity="HIGH", affected_entity="Item", metric_name="price", observed_value=-5.0, expected_value=0.0, deviation_pct=100.0, confidence=0.95, reasoning="Negative price"),),
        overall_health_score=87.0,
        domain=DatasetDomain.RETAIL,
    )

    exec_summary = generator.generate(dataset_profile, business_profile, intel_report)

    assert isinstance(exec_summary, ExecutiveSummary)
    assert exec_summary.dataset_name == "transactions.csv"
    assert exec_summary.domain == DatasetDomain.RETAIL
    assert "transactions.csv" in exec_summary.overview
    assert "87.0%" in exec_summary.data_quality_summary
    assert len(exec_summary.major_findings) > 0
    assert len(exec_summary.top_risks) > 0
    assert len(exec_summary.recommended_actions) > 0
