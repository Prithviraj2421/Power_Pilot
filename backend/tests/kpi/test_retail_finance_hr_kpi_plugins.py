from app.common.enums import DatasetDomain, PhysicalType
from app.intelligence.kpi.candidate import KPICandidate
from app.intelligence.kpi.ir import Difference, Measure, Op, Ratio, columns_of
from app.intelligence.kpi.plugins.finance_kpi_plugin import FinanceKPIPlugin
from app.intelligence.kpi.plugins.hr_kpi_plugin import HRKPIPlugin
from app.intelligence.kpi.plugins.retail_kpi_plugin import RetailKPIPlugin

I, F, T = PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.TEXT


def test_retail_kpi_plugin_proposes_expressions_over_the_real_columns(make_profile) -> None:
    profile = make_profile(
        "transactions.csv", DatasetDomain.RETAIL,
        ("Order ID", T, True), ("Customer ID", T, True), ("Quantity", I), ("Sales", F),
    )

    results = {k.name: k for k in RetailKPIPlugin().recommend(profile)}

    assert set(results) == {
        "Total Sales Revenue", "Average Order Value (AOV)", "Total Units Sold", "Active Customer Count",
    }
    assert all(isinstance(k, KPICandidate) for k in results.values())
    assert results["Total Sales Revenue"].expression == Measure(Op.SUM, "Sales")
    assert isinstance(results["Average Order Value (AOV)"].expression, Ratio)
    assert columns_of(results["Average Order Value (AOV)"].expression) == ("Sales", "Order ID")


def test_a_kpi_whose_column_is_missing_is_skipped_not_guessed(make_profile) -> None:
    profile = make_profile("t.csv", DatasetDomain.RETAIL, ("Sales", F))  # no order, quantity or customer column

    assert [k.name for k in RetailKPIPlugin().recommend(profile)] == ["Total Sales Revenue"]


def test_example_targets_are_kept_separate_from_the_expression(make_profile) -> None:
    profile = make_profile("t.csv", DatasetDomain.RETAIL, ("Sales", F))

    (kpi,) = RetailKPIPlugin().recommend(profile)

    assert kpi.example_target == "> +5% MoM Growth"


def test_finance_kpi_plugin(make_profile) -> None:
    profile = make_profile(
        "ledger.csv", DatasetDomain.FINANCE, ("Revenue", F), ("Operating_Expenses", F),
    )

    results = {k.name: k for k in FinanceKPIPlugin().recommend(profile)}

    assert len(results) == 3
    assert results["Net EBITDA Profit"].expression == Difference(
        Measure(Op.SUM, "Revenue"), Measure(Op.SUM, "Operating_Expenses")
    )


def test_finance_never_subtracts_a_column_from_itself(make_profile) -> None:
    # Only one money column: revenue and expenses would both resolve to it.
    profile = make_profile("ledger.csv", DatasetDomain.FINANCE, ("amount", F))

    assert [k.name for k in FinanceKPIPlugin().recommend(profile)] == ["Gross Operating Revenue"]


def test_hr_kpi_plugin(make_profile) -> None:
    profile = make_profile(
        "employees.csv", DatasetDomain.HR,
        ("Employee_ID", T, True), ("Salary", F), ("Tenure_Years", F),
    )

    results = HRKPIPlugin().recommend(profile)

    assert len(results) == 3
    assert any("Headcount" in k.name for k in results)
