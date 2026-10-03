import pytest

from app.common.enums import DatasetDomain, PhysicalType, Priority
from app.intelligence.kpi.plugins.fallback_kpi_plugin import FallbackKPIPlugin
from app.intelligence.kpi.plugins.healthcare_kpi_plugin import HealthcareKPIPlugin
from app.intelligence.kpi.plugins.logistics_kpi_plugin import LogisticsKPIPlugin
from app.intelligence.kpi.plugins.marketing_kpi_plugin import MarketingKPIPlugin
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile
from app.models.kpi_recommendation import KPIRecommendation


def make_col(name: str, ptype: PhysicalType) -> ColumnProfile:
    return ColumnProfile(name=name, physical_type=ptype, nullable=False, unique=False, identifier=False, missing_count=0, unique_count=10)


def test_healthcare_kpi_plugin(make_profile) -> None:
    plugin = HealthcareKPIPlugin()
    profile = make_profile(
        "admissions.csv", DatasetDomain.HEALTHCARE,
        ("Patient_ID", PhysicalType.TEXT, True),
        ("Length_Of_Stay_Days", PhysicalType.INTEGER),
        ("Treatment_Cost", PhysicalType.FLOAT),
    )

    results = plugin.recommend(profile)
    assert isinstance(results, tuple)
    assert len(results) >= 3
    assert any("Patient" in k.name or "Stay" in k.name for k in results)


def test_marketing_kpi_plugin(make_profile) -> None:
    plugin = MarketingKPIPlugin()
    profile = make_profile(
        "campaigns.csv", DatasetDomain.MARKETING,
        ("Revenue", PhysicalType.FLOAT), ("Ad_Spend", PhysicalType.FLOAT),
        ("Conversions", PhysicalType.INTEGER), ("Clicks", PhysicalType.INTEGER),
        ("Impressions", PhysicalType.INTEGER),
    )

    results = plugin.recommend(profile)
    assert isinstance(results, tuple)
    assert len(results) >= 3
    assert any("ROAS" in k.name for k in results)


def test_logistics_kpi_plugin(make_profile) -> None:
    plugin = LogisticsKPIPlugin()
    profile = make_profile(
        "shipments.csv", DatasetDomain.LOGISTICS,
        ("Freight_Cost", PhysicalType.FLOAT), ("Delay_Days", PhysicalType.INTEGER),
        ("Quantity_Shipped", PhysicalType.INTEGER),
    )

    results = plugin.recommend(profile)
    assert isinstance(results, tuple)
    assert len(results) >= 3
    assert any("Freight" in k.name or "Delay" in k.name for k in results)


def test_fallback_kpi_plugin() -> None:
    plugin = FallbackKPIPlugin()
    cols = [make_col("sales_amt", PhysicalType.FLOAT), make_col("region_name", PhysicalType.TEXT)]
    profile = DatasetProfile(dataset_name="custom_data", total_rows=100, total_columns=2, columns=cols, detected_domain=DatasetDomain.UNKNOWN)

    results = plugin.recommend(profile)
    assert isinstance(results, tuple)
    assert len(results) >= 1
    assert any("Sales Amt" in k.name for k in results)


def test_fallback_skips_identifier_and_code_columns(make_profile) -> None:
    profile = make_profile(
        "customers.csv", DatasetDomain.UNKNOWN,
        ("Row ID", PhysicalType.INTEGER), ("Postal Code", PhysicalType.FLOAT),
        ("customer_id", PhysicalType.INTEGER, True), ("Revenue", PhysicalType.FLOAT),
    )

    names = [k.name for k in FallbackKPIPlugin().recommend(profile)]

    assert names == ["Total Revenue"], "summing an ID or a postal code is meaningless"


def test_fallback_does_not_double_the_total_prefix(make_profile) -> None:
    profile = make_profile("homes.csv", DatasetDomain.UNKNOWN, ("total_sqft", PhysicalType.FLOAT))

    assert [k.name for k in FallbackKPIPlugin().recommend(profile)] == ["Total Sqft"]


def test_engine_falls_back_when_the_domain_plugin_finds_none_of_its_columns(make_dataset) -> None:
    from app.intelligence.kpi_engine import KPIEngine

    # Classified retail, but nothing in it looks like revenue, orders, quantity or customers.
    profile, df = make_dataset("odd.csv", DatasetDomain.RETAIL, ("temperature_c", PhysicalType.FLOAT))

    report = KPIEngine().recommend(profile, df=df)

    assert report.total_kpis_recommended == 1
    assert report.all_kpis[0].formula == "SUM('odd'[temperature_c])"
    assert report.all_kpis[0].verified is True
