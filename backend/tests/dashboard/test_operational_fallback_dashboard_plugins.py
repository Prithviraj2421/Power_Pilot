import pytest

from app.common.enums import DatasetDomain, PhysicalType
from app.intelligence.dashboard.plugins.fallback_dashboard_plugin import FallbackDashboardPlugin
from app.intelligence.dashboard.plugins.healthcare_dashboard_plugin import HealthcareDashboardPlugin
from app.intelligence.dashboard.plugins.logistics_dashboard_plugin import LogisticsDashboardPlugin
from app.intelligence.dashboard.plugins.marketing_dashboard_plugin import MarketingDashboardPlugin
from app.models.column_profile import ColumnProfile
from app.models.dashboard_models import DashboardRecommendationReport
from app.models.dataset_profile import DatasetProfile


def make_col(name: str, ptype: PhysicalType) -> ColumnProfile:
    return ColumnProfile(name=name, physical_type=ptype, nullable=False, unique=False, identifier=False, missing_count=0, unique_count=10)


def test_healthcare_dashboard_plugin() -> None:
    plugin = HealthcareDashboardPlugin()
    profile = DatasetProfile(dataset_name="admissions", total_rows=100, total_columns=5, detected_domain=DatasetDomain.HEALTHCARE)

    report = plugin.recommend(profile)
    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.HEALTHCARE
    assert len(report.tabs) >= 1


def test_marketing_dashboard_plugin() -> None:
    plugin = MarketingDashboardPlugin()
    profile = DatasetProfile(dataset_name="campaigns", total_rows=100, total_columns=5, detected_domain=DatasetDomain.MARKETING)

    report = plugin.recommend(profile)
    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.MARKETING
    assert len(report.tabs) >= 1


def test_logistics_dashboard_plugin() -> None:
    plugin = LogisticsDashboardPlugin()
    profile = DatasetProfile(dataset_name="shipments", total_rows=100, total_columns=5, detected_domain=DatasetDomain.LOGISTICS)

    report = plugin.recommend(profile)
    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.LOGISTICS
    assert len(report.tabs) >= 1


def test_fallback_dashboard_plugin() -> None:
    plugin = FallbackDashboardPlugin()
    cols = [make_col("sales_amt", PhysicalType.FLOAT), make_col("region_name", PhysicalType.TEXT)]
    profile = DatasetProfile(dataset_name="custom_data", total_rows=100, total_columns=2, columns=cols, detected_domain=DatasetDomain.UNKNOWN)

    report = plugin.recommend(profile)
    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.UNKNOWN
    assert len(report.tabs) >= 1
