from app.common.enums import DatasetDomain, PhysicalType
from app.intelligence.dashboard_engine import DashboardEngine
from app.models.dashboard_models import DashboardRecommendationReport

I, F, T = PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.TEXT
DT = PhysicalType.DATETIME


def test_dashboard_engine_orchestrator(make_profile) -> None:
    profile = make_profile(
        "pos_transactions.csv", DatasetDomain.RETAIL,
        ("Order ID", T, True), ("Order Date", DT), ("Category", T), ("Region", T),
        ("Product Name", T), ("Quantity", I), ("Sales", F),
    )

    report = DashboardEngine().recommend(profile)

    assert isinstance(report, DashboardRecommendationReport)
    assert report.domain == DatasetDomain.RETAIL
    assert len(report.tabs) >= 2
    assert len(report.global_filters) >= 2


def test_engine_falls_back_when_a_domain_plugin_finds_none_of_its_columns(make_profile) -> None:
    # Classified retail, but there is nothing in it a retail dashboard could chart.
    profile = make_profile("odd.csv", DatasetDomain.RETAIL, ("temperature_c", F), ("sensor", T))

    report = DashboardEngine().recommend(profile)

    assert report.tabs, "an empty dashboard is worse than a generic one"
    assert report.domain == DatasetDomain.UNKNOWN
