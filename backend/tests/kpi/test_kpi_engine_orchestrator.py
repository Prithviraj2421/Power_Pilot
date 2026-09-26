import pytest

from app.common.enums import DatasetDomain, Priority
from app.intelligence.kpi_engine import KPIEngine
from app.models.dataset_profile import DatasetProfile
from app.models.kpi_recommendation import KPIRecommendation
from app.models.kpi_report import KPIReport


def test_kpi_engine_orchestrator() -> None:
    engine = KPIEngine()

    profile = DatasetProfile(dataset_name="pos_transactions", total_rows=500, total_columns=6, detected_domain=DatasetDomain.RETAIL)

    report = engine.recommend(profile)

    assert isinstance(report, KPIReport)
    assert report.domain == DatasetDomain.RETAIL
    assert report.total_kpis_recommended >= 4
    assert len(report.primary_kpis) == 3
    assert len(report.secondary_kpis) >= 1

    # Verify primary KPI priority sorting
    first_kpi = report.primary_kpis[0]
    assert isinstance(first_kpi, KPIRecommendation)
    assert first_kpi.priority == Priority.CRITICAL
