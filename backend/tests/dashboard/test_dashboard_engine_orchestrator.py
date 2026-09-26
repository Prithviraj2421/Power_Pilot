import pytest

from app.common.enums import DatasetDomain
from app.intelligence.dashboard_engine import DashboardEngine
from app.models.dashboard_models import DashboardRecommendationReport
from app.models.dataset_profile import DatasetProfile


def test_dashboard_engine_orchestrator() -> None:
    engine = DashboardEngine()

    profile = DatasetProfile(dataset_name="pos_transactions", total_rows=500, total_columns=6, detected_domain=DatasetDomain.RETAIL)

    report = engine.recommend(profile)

    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.RETAIL
    assert len(report.tabs) >= 2
    assert len(report.global_filters) >= 2
