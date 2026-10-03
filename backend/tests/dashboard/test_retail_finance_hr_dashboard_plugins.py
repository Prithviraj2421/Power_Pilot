import pytest

from app.common.enums import DatasetDomain, PhysicalType
from app.intelligence.kpi_engine import KPIEngine
from app.intelligence.dashboard.plugins.finance_dashboard_plugin import FinanceDashboardPlugin
from app.intelligence.dashboard.plugins.hr_dashboard_plugin import HRDashboardPlugin
from app.intelligence.dashboard.plugins.retail_dashboard_plugin import RetailDashboardPlugin
from app.models.dashboard_models import DashboardRecommendationReport, DashboardTab
from app.models.dataset_profile import DatasetProfile


I, F, T = PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.TEXT
DT = PhysicalType.DATETIME


def test_retail_dashboard_plugin(make_dataset) -> None:
    plugin = RetailDashboardPlugin()
    profile, df = make_dataset(
        "transactions.csv", DatasetDomain.RETAIL,
        ("Order ID", T, True), ("Customer ID", T, True), ("Order Date", DT), ("Category", T),
        ("Region", T), ("Product Name", T), ("Quantity", I), ("Sales", F),
    )

    report = plugin.recommend(profile, kpi_report=KPIEngine().recommend(profile, df=df))
    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.RETAIL
    assert len(report.tabs) >= 2
    tab1 = report.tabs[0]
    assert isinstance(tab1, DashboardTab)
    assert len(tab1.widgets) >= 4, "four KPI cards plus the revenue charts"


def test_finance_dashboard_plugin(make_profile) -> None:
    plugin = FinanceDashboardPlugin()
    profile = make_profile(
        "ledger.csv", DatasetDomain.FINANCE,
        ("Revenue", F), ("Operating_Expenses", F), ("Ledger_Account", T), ("Department", T),
    )

    report = plugin.recommend(profile)
    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.FINANCE
    assert len(report.tabs) >= 1
    assert "P&L" in report.dashboard_title or "Financial" in report.dashboard_title


def test_hr_dashboard_plugin(make_profile) -> None:
    plugin = HRDashboardPlugin()
    profile = make_profile(
        "employees.csv", DatasetDomain.HR,
        ("Employee_ID", T, True), ("Salary", F), ("Department", T),
    )

    report = plugin.recommend(profile)
    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.HR
    assert len(report.tabs) >= 1
    assert "HR" in report.dashboard_title or "Workforce" in report.dashboard_title
