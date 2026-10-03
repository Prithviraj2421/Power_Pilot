from app.common.enums import DatasetDomain
from app.intelligence.kpi.plugins.finance_kpi_plugin import FinanceKPIPlugin
from app.intelligence.kpi.plugins.hr_kpi_plugin import HRKPIPlugin
from app.intelligence.kpi.plugins.retail_kpi_plugin import RetailKPIPlugin
from app.models.kpi_recommendation import KPIRecommendation

from tests.kpi.conftest import F, I, T


def test_retail_kpi_plugin(make_profile) -> None:
    profile = make_profile(
        "transactions.csv", DatasetDomain.RETAIL,
        ("Order ID", T, True), ("Customer ID", T, True), ("Quantity", I), ("Sales", F),
    )

    results = RetailKPIPlugin().recommend(profile)

    assert isinstance(results, tuple)
    assert len(results) == 4
    for kpi in results:
        assert isinstance(kpi, KPIRecommendation)
        assert kpi.formula is not None
        assert kpi.target_threshold is not None


def test_finance_kpi_plugin(make_profile) -> None:
    profile = make_profile(
        "ledger.csv", DatasetDomain.FINANCE, ("Revenue", F), ("Operating_Expenses", F),
    )

    results = FinanceKPIPlugin().recommend(profile)

    assert len(results) == 3
    assert any("EBITDA" in k.name for k in results)


def test_hr_kpi_plugin(make_profile) -> None:
    profile = make_profile(
        "employees.csv", DatasetDomain.HR,
        ("Employee_ID", T, True), ("Salary", F), ("Tenure_Years", F),
    )

    results = HRKPIPlugin().recommend(profile)

    assert len(results) == 3
    assert any("Headcount" in k.name for k in results)
