import pytest

from app.common.enums import DatasetDomain, Priority
from app.intelligence.kpi.plugins.finance_kpi_plugin import FinanceKPIPlugin
from app.intelligence.kpi.plugins.hr_kpi_plugin import HRKPIPlugin
from app.intelligence.kpi.plugins.retail_kpi_plugin import RetailKPIPlugin
from app.models.dataset_profile import DatasetProfile
from app.models.kpi_recommendation import KPIRecommendation


def test_retail_kpi_plugin() -> None:
    plugin = RetailKPIPlugin()
    profile = DatasetProfile(dataset_name="transactions", total_rows=100, total_columns=5, detected_domain=DatasetDomain.RETAIL)

    results = plugin.recommend(profile)
    assert isinstance(results, tuple)
    assert len(results) >= 3
    for kpi in results:
        assert isinstance(kpi, KPIRecommendation)
        assert kpi.formula is not None
        assert kpi.target_threshold is not None


def test_finance_kpi_plugin() -> None:
    plugin = FinanceKPIPlugin()
    profile = DatasetProfile(dataset_name="ledger", total_rows=100, total_columns=5, detected_domain=DatasetDomain.FINANCE)

    results = plugin.recommend(profile)
    assert isinstance(results, tuple)
    assert len(results) >= 3
    assert any("EBITDA" in k.name for k in results)


def test_hr_kpi_plugin() -> None:
    plugin = HRKPIPlugin()
    profile = DatasetProfile(dataset_name="employees", total_rows=100, total_columns=5, detected_domain=DatasetDomain.HR)

    results = plugin.recommend(profile)
    assert isinstance(results, tuple)
    assert len(results) >= 3
    assert any("Headcount" in k.name for k in results)
