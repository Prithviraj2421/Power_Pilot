from app.common.enums import DatasetDomain, PhysicalType, Priority
from app.intelligence.kpi_engine import KPIEngine
from app.models.kpi_recommendation import KPIRecommendation
from app.models.kpi_report import KPIReport

I, F, T = PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.TEXT

RETAIL = (("Order ID", T, True), ("Customer ID", T, True), ("Quantity", I), ("Sales", F))


def test_kpi_engine_orchestrator(make_dataset) -> None:
    profile, df = make_dataset("pos_transactions.csv", DatasetDomain.RETAIL, *RETAIL)

    report = KPIEngine().recommend(profile, df=df)

    assert isinstance(report, KPIReport)
    assert report.domain == DatasetDomain.RETAIL
    assert report.total_kpis_recommended == 4
    assert len(report.primary_kpis) == 3
    assert len(report.secondary_kpis) == 1
    assert report.rejected_kpis == ()

    first_kpi = report.primary_kpis[0]
    assert isinstance(first_kpi, KPIRecommendation)
    assert first_kpi.priority == Priority.CRITICAL


def test_every_reported_kpi_is_verified_and_carries_its_value(make_dataset) -> None:
    profile, df = make_dataset("pos_transactions.csv", DatasetDomain.RETAIL, *RETAIL)

    report = KPIEngine().recommend(profile, df=df)

    revenue = next(k for k in report.all_kpis if k.name == "Total Sales Revenue")
    assert all(k.verified and k.computed_value is not None for k in report.all_kpis)
    assert revenue.computed_value == float(df["Sales"].sum())
    assert revenue.formula == "SUM('pos_transactions'[Sales])"


def test_without_a_dataset_nothing_can_be_verified_so_nothing_is_reported(make_dataset) -> None:
    profile, _ = make_dataset("pos_transactions.csv", DatasetDomain.RETAIL, *RETAIL)

    report = KPIEngine().recommend(profile)

    assert report.total_kpis_recommended == 0
    assert report.rejected_kpis, "the proposals are kept, with the reason they were not trusted"
    assert all("no dataset" in k.verification_note for k in report.rejected_kpis)
