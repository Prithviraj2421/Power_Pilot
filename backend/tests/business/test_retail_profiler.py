import pytest
from app.intelligence.business.profilers.retail_profiler import RetailProfiler
from app.models.dataset_profile import DatasetProfile
from app.common.enums import DatasetDomain, Priority
from app.models.business_profile import BusinessProfile

def test_retail_profiler_returns_correct_profile() -> None:
    """
    Test RetailProfiler with a DatasetProfile (domain=RETAIL).
    Asserts BusinessProfile is returned with correct primary KPIs (Revenue, AOV, Units Sold, Active Customers),
    secondary KPIs, dimensions, measures, business questions, suggested charts, dashboard layout, filters, 
    and time intelligence. Also asserts kpi.reason and kpi.confidence.
    """
    profiler = RetailProfiler()
    dataset_profile = DatasetProfile(
        dataset_name="Retail_Sales",
        total_rows=1000,
        total_columns=10,
        detected_domain=DatasetDomain.RETAIL
    )

    business_profile: BusinessProfile = profiler.profile(dataset_profile=dataset_profile)

    assert isinstance(business_profile, BusinessProfile)
    assert business_profile.domain == DatasetDomain.RETAIL

    # Primary KPIs
    assert len(business_profile.primary_kpis) == 4
    kpi_names = [kpi.name for kpi in business_profile.primary_kpis]
    assert "Total Revenue" in kpi_names
    assert "Average Order Value (AOV)" in kpi_names
    assert "Total Units Sold" in kpi_names
    assert "Active Customer Count" in kpi_names

    # Check reason and confidence for all primary KPIs for explainability
    for kpi in business_profile.primary_kpis:
        assert kpi.confidence > 0.0
        assert kpi.reason is not None
        assert len(kpi.reason) > 0

    # Secondary KPIs
    assert len(business_profile.secondary_kpis) == 2
    secondary_kpi_names = [kpi.name for kpi in business_profile.secondary_kpis]
    assert "Revenue Per Customer" in secondary_kpi_names
    assert "Average Basket Size" in secondary_kpi_names

    # Dimensions & Measures
    assert "Product_Category" in business_profile.dimensions
    assert "Store_Region" in business_profile.dimensions
    assert "Revenue" in business_profile.measures
    assert "Quantity" in business_profile.measures

    # Business Questions
    assert len(business_profile.business_questions) == 4
    assert any("revenue" in q.lower() for q in business_profile.business_questions)

    # Suggested charts
    assert len(business_profile.suggested_charts) == 3
    chart_titles = [chart.get("title") for chart in business_profile.suggested_charts]
    assert "Monthly Revenue Trend" in chart_titles

    # Dashboard layout
    assert len(business_profile.suggested_dashboard_layout) == 3
    sections = [layout.get("section") for layout in business_profile.suggested_dashboard_layout]
    assert "Header" in sections
    
    # Filters & Time intelligence
    assert "Order_Date" in business_profile.suggested_filters
    assert len(business_profile.time_intelligence) == 3
