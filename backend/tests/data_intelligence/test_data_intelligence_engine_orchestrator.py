import pandas as pd
import pytest

from app.common.enums import DatasetDomain
from app.intelligence.data_intelligence_engine import DataIntelligenceEngine
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport, InsightCandidate
from app.models.dataset_profile import DatasetProfile


def test_data_intelligence_engine_orchestrator() -> None:
    """Test DataIntelligenceEngine orchestrator facade analyzes DataFrame and produces unified report."""
    engine = DataIntelligenceEngine()

    df = pd.DataFrame({
        "order_date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]),
        "units": [10, 20, 30, 40, 50],
        "revenue": [100.0, 200.0, 300.0, 400.0, 500.0],
        "customer": ["C1", "C2", "C3", "C4", "C5"],
    })

    dataset_profile = DatasetProfile(
        dataset_name="transactions.csv",
        total_rows=5,
        total_columns=4,
        detected_domain=DatasetDomain.RETAIL,
    )

    business_profile = BusinessProfile(
        domain=DatasetDomain.RETAIL,
        confidence=0.9,
        business_context="Retail transaction analytics",
        executive_summary="Retail summary",
    )

    report = engine.analyze(df, dataset_profile, business_profile, entities=None)

    assert isinstance(report, DataIntelligenceReport)
    assert report.domain == DatasetDomain.RETAIL
    assert 0.0 <= report.overall_health_score <= 100.0
    assert report.quality_report is not None
    assert report.statistical_summary is not None
    assert isinstance(report.insights, tuple)
    assert all(isinstance(ins, InsightCandidate) for ins in report.insights)
