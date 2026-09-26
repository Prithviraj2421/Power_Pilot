import pytest
from app.intelligence.business.profilers.finance_profiler import FinanceProfiler
from app.intelligence.business.profilers.hr_profiler import HRProfiler
from app.models.dataset_profile import DatasetProfile
from app.common.enums import DatasetDomain, Priority
from app.models.business_profile import BusinessProfile

def test_finance_profiler_returns_correct_profile() -> None:
    """
    Test FinanceProfiler with a Finance dataset profile.
    Asserts P&L KPIs, revenue, net profit, waterfall charts, and other attributes.
    """
    profiler = FinanceProfiler()
    dataset_profile = DatasetProfile(
        dataset_name="Finance_Ledger",
        total_rows=5000,
        total_columns=20,
        detected_domain=DatasetDomain.FINANCE
    )

    business_profile: BusinessProfile = profiler.profile(dataset_profile=dataset_profile)

    assert isinstance(business_profile, BusinessProfile)
    assert business_profile.domain == DatasetDomain.FINANCE

    kpi_names = [kpi.name for kpi in business_profile.primary_kpis]
    assert "Gross Revenue" in kpi_names
    assert "Net Profit" in kpi_names
    assert "Operating Expenses" in kpi_names

    # Explainability checks
    for kpi in business_profile.primary_kpis:
        assert kpi.confidence > 0.0
        assert kpi.reason

    # Waterfall chart for P&L
    has_waterfall = any(chart.get("chart_type") == "waterfall" for chart in business_profile.suggested_charts)
    assert has_waterfall

    # P&L in layout
    layout_sections = [layout.get("title") for layout in business_profile.suggested_dashboard_layout]
    assert any("Profitability" in section for section in layout_sections)

    # Dimensions & Measures
    assert "Account_Category" in business_profile.dimensions
    assert "Gross_Revenue" in business_profile.measures


def test_hr_profiler_returns_correct_profile() -> None:
    """
    Test HRProfiler with an HR dataset profile.
    Asserts headcount, salary, tenure KPIs, and department breakdown charts.
    """
    profiler = HRProfiler()
    dataset_profile = DatasetProfile(
        dataset_name="Employee_Data",
        total_rows=3000,
        total_columns=15,
        detected_domain=DatasetDomain.HR
    )

    business_profile: BusinessProfile = profiler.profile(dataset_profile=dataset_profile)

    assert isinstance(business_profile, BusinessProfile)
    assert business_profile.domain == DatasetDomain.HR

    kpi_names = [kpi.name for kpi in business_profile.primary_kpis]
    assert "Total Headcount" in kpi_names
    assert "Total Payroll Spend" in kpi_names
    assert "Average Salary" in kpi_names
    assert "Average Tenure (Years)" in kpi_names

    # Explainability checks
    for kpi in business_profile.primary_kpis:
        assert kpi.confidence > 0.0
        assert kpi.reason

    # Department breakdown charts
    chart_titles = [chart.get("title") for chart in business_profile.suggested_charts]
    assert any("Department" in title for title in chart_titles)

    # Layout check
    layout_sections = [layout.get("section") for layout in business_profile.suggested_dashboard_layout]
    assert "Department Breakdown" in layout_sections

    # Dimensions & Measures
    assert "Department" in business_profile.dimensions
    assert "Salary" in business_profile.measures
