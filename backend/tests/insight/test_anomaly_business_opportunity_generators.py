import pytest

from app.common.enums import DatasetDomain, Priority
from app.intelligence.insight.generators.anomaly_insights_generator import AnomalyInsightsGenerator
from app.intelligence.insight.generators.business_rule_insights_generator import BusinessRuleInsightsGenerator
from app.intelligence.insight.generators.opportunity_insights_generator import OpportunityInsightsGenerator
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import (
    BusinessAnomaly,
    DataIntelligenceReport,
    OutlierReport,
    PatternReport,
    QualityReport,
    StatisticalSummary,
)
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import Insight


def test_anomaly_insights_generator() -> None:
    generator = AnomalyInsightsGenerator()
    dataset_profile = DatasetProfile(dataset_name="retail.csv", total_rows=100, total_columns=5, detected_domain=DatasetDomain.RETAIL)
    business_profile = BusinessProfile(domain=DatasetDomain.RETAIL, confidence=0.9, business_context="Retail", executive_summary="Retail summary")

    anomalies = (
        BusinessAnomaly(anomaly_title="Negative Pricing", severity="HIGH", affected_entity="Product", metric_name="price", observed_value=-10.0, expected_value=0.0, deviation_pct=100.0, confidence=0.95, reasoning="Negative price.", evidence=("1 negative price",)),
    )
    outliers = (
        OutlierReport(column_name="price", outlier_count=10, outlier_percentage=10.0, method_used="IQR", outlier_bounds=(-50.0, 500.0), confidence=0.7, reasoning="IQR outliers"),
    )
    intel_report = DataIntelligenceReport(
        quality_report=QualityReport(overall_score=80.0, completeness_score=80.0, uniqueness_score=100.0, validity_score=80.0, total_issues=2),
        statistical_summary=StatisticalSummary(total_rows=100, numeric_columns_count=1, categorical_columns_count=1, date_columns_count=0),
        business_anomalies=anomalies,
        outliers=outliers,
        domain=DatasetDomain.RETAIL,
    )

    results = generator.generate(dataset_profile, business_profile, intel_report)
    assert isinstance(results, tuple)
    assert len(results) == 2
    for ins in results:
        assert isinstance(ins, Insight)
        assert ins.category == "ANOMALY"


def test_business_rule_insights_generator() -> None:
    generator = BusinessRuleInsightsGenerator()
    dataset_profile = DatasetProfile(dataset_name="finance.csv", total_rows=50, total_columns=3, detected_domain=DatasetDomain.FINANCE)
    business_profile = BusinessProfile(domain=DatasetDomain.FINANCE, confidence=0.92, business_context="Finance ledger", executive_summary="Finance summary")
    intel_report = DataIntelligenceReport(
        quality_report=QualityReport(overall_score=100.0, completeness_score=100.0, uniqueness_score=100.0, validity_score=100.0, total_issues=0),
        statistical_summary=StatisticalSummary(total_rows=50, numeric_columns_count=2, categorical_columns_count=1, date_columns_count=0),
        domain=DatasetDomain.FINANCE,
    )

    results = generator.generate(dataset_profile, business_profile, intel_report)
    assert isinstance(results, tuple)
    assert len(results) >= 1
    insight = results[0]
    assert isinstance(insight, Insight)
    assert insight.category == "BUSINESS_RULE"
    assert "Financial" in insight.title or "Margin" in insight.title


def test_opportunity_insights_generator() -> None:
    generator = OpportunityInsightsGenerator()
    dataset_profile = DatasetProfile(dataset_name="sales.csv", total_rows=100, total_columns=4, detected_domain=DatasetDomain.RETAIL)
    business_profile = BusinessProfile(domain=DatasetDomain.RETAIL, confidence=0.9, business_context="Retail", executive_summary="Retail summary")
    patterns = (
        PatternReport(pattern_type="Pareto Distribution", description="Top 20% categories account for 85% revenue.", affected_columns=("category", "revenue"), confidence=0.9, reasoning="80/20 rule"),
    )
    intel_report = DataIntelligenceReport(
        quality_report=QualityReport(overall_score=85.0, completeness_score=85.0, uniqueness_score=100.0, validity_score=85.0, total_issues=1),
        statistical_summary=StatisticalSummary(total_rows=100, numeric_columns_count=2, categorical_columns_count=2, date_columns_count=0),
        patterns=patterns,
        domain=DatasetDomain.RETAIL,
    )

    results = generator.generate(dataset_profile, business_profile, intel_report)
    assert isinstance(results, tuple)
    assert len(results) >= 1
    insight = results[0]
    assert isinstance(insight, Insight)
    assert insight.category == "OPPORTUNITY"
