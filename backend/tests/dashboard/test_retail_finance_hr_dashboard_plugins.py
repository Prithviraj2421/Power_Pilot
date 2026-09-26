import pytest

from app.common.enums import DatasetDomain
from app.intelligence.dashboard.plugins.finance_dashboard_plugin import FinanceDashboardPlugin
from app.intelligence.dashboard.plugins.hr_dashboard_plugin import HRDashboardPlugin
from app.intelligence.dashboard.plugins.retail_dashboard_plugin import RetailDashboardPlugin
from app.models.dashboard_models import DashboardRecommendationReport, DashboardTab
from app.models.dataset_profile import DatasetProfile


def test_retail_dashboard_plugin() -> None:
    plugin = RetailDashboardPlugin()
    profile = DatasetProfile(dataset_name="transactions", total_rows=100, total_columns=5, detected_domain=DatasetDomain.RETAIL)

    report = plugin.recommend(profile)
    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.RETAIL
    assert len(report.tabs) >= 2
    tab1 = report.tabs[0]
    assert isinstance(tab1, DashboardTab)
    assert len(tab1.widgets) >= 4


def test_finance_dashboard_plugin() -> None:
    plugin = FinanceDashboardPlugin()
    profile = DatasetProfile(dataset_name="ledger", total_rows=100, total_columns=5, detected_domain=DatasetDomain.FINANCE)

    report = plugin.recommend(profile)
    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.FINANCE
    assert len(report.tabs) >= 1
    assert "P&L" in report.dashboard_title or "Financial" in report.dashboard_title


def test_hr_dashboard_plugin() -> None:
    plugin = HRDashboardPlugin()
    profile = DatasetProfile(dataset_name="employees", total_rows=100, total_columns=5, detected_domain=DatasetDomain.HR)

    report = plugin.recommend(profile)
    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.HR
    assert len(report.tabs) >= 1
    assert "HR" in report.dashboard_title or "Workforce" in report.dashboard_title
