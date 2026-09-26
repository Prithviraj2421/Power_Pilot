import pandas as pd
import pytest

from app.common.enums import DatasetDomain
from app.intelligence.data.plugins.business_anomalies_plugin import BusinessAnomaliesPlugin
from app.intelligence.data.plugins.patterns_plugin import PatternsPlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import BusinessAnomaly, PatternReport
from app.models.dataset_profile import DatasetProfile


def test_patterns_plugin_pareto() -> None:
    """Test PatternsPlugin with Pareto 80/20 distribution."""
    plugin = PatternsPlugin()

    # Category A drives 90% of revenue
    df = pd.DataFrame({
        "category": ["A"] * 9 + ["B", "C"],
        "revenue": [1000] * 9 + [10, 10],
    })

    dataset_profile = DatasetProfile(dataset_name="sales.csv", total_rows=11, total_columns=2)
    results = plugin.analyze(df, dataset_profile)

    assert isinstance(results, (list, tuple))
    assert len(results) >= 1
    pattern = results[0]
    assert isinstance(pattern, PatternReport)
    assert pattern.confidence >= 0.5


def test_business_anomalies_plugin_retail() -> None:
    """Test BusinessAnomaliesPlugin for Retail negative prices."""
    plugin = BusinessAnomaliesPlugin()

    df = pd.DataFrame({
        "sales": [100.0, -50.0, 200.0],
        "quantity": [1, 2, 3],
    })

    dataset_profile = DatasetProfile(
        dataset_name="retail.csv", total_rows=3, total_columns=2, detected_domain=DatasetDomain.RETAIL
    )
    business_profile = BusinessProfile(
        domain=DatasetDomain.RETAIL,
        confidence=0.9,
        business_context="Retail sales",
        executive_summary="Retail summary",
    )

    results = plugin.analyze(df, dataset_profile, business_profile)

    assert isinstance(results, (list, tuple))
    assert len(results) >= 1
    anomaly = results[0]
    assert isinstance(anomaly, BusinessAnomaly)
    assert anomaly.severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
    assert len(anomaly.evidence) > 0


def test_business_anomalies_plugin_finance() -> None:
    """Test BusinessAnomaliesPlugin for Finance domain rules."""
    plugin = BusinessAnomaliesPlugin()

    df = pd.DataFrame({
        "gross_revenue": [1000.0, 2000.0, 1500.0],
        "operating_cost": [-500.0, 300.0, 400.0],  # Negative cost is an anomaly
    })

    dataset_profile = DatasetProfile(
        dataset_name="ledger.csv", total_rows=3, total_columns=2, detected_domain=DatasetDomain.FINANCE
    )
    business_profile = BusinessProfile(
        domain=DatasetDomain.FINANCE,
        confidence=0.9,
        business_context="Financial ledger",
        executive_summary="Finance summary",
    )

    results = plugin.analyze(df, dataset_profile, business_profile)

    assert isinstance(results, (list, tuple))
    assert len(results) >= 1
    anomaly = results[0]
    assert isinstance(anomaly, BusinessAnomaly)
    assert "cost" in anomaly.anomaly_title.lower() or "expense" in anomaly.anomaly_title.lower() or "finance" in anomaly.anomaly_title.lower() or "negative" in anomaly.anomaly_title.lower()
