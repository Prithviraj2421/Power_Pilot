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


def test_healthcare_kpi_plugin() -> None:
    plugin = HealthcareKPIPlugin()
    profile = DatasetProfile(dataset_name="admissions", total_rows=100, total_columns=5, detected_domain=DatasetDomain.HEALTHCARE)

    results = plugin.recommend(profile)
    assert isinstance(results, tuple)
    assert len(results) >= 3
    assert any("Patient" in k.name or "Stay" in k.name for k in results)


def test_marketing_kpi_plugin() -> None:
    plugin = MarketingKPIPlugin()
    profile = DatasetProfile(dataset_name="campaigns", total_rows=100, total_columns=5, detected_domain=DatasetDomain.MARKETING)

    results = plugin.recommend(profile)
    assert isinstance(results, tuple)
    assert len(results) >= 3
    assert any("ROAS" in k.name for k in results)


def test_logistics_kpi_plugin() -> None:
    plugin = LogisticsKPIPlugin()
    profile = DatasetProfile(dataset_name="shipments", total_rows=100, total_columns=5, detected_domain=DatasetDomain.LOGISTICS)

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
