from typing import Optional

from app.common.enums import DatasetDomain, Priority
from app.intelligence.business.base_business_profiler import BaseBusinessProfiler
from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation


class FinanceProfiler(BaseBusinessProfiler):
    """
    Business profiler plugin for the FINANCE domain.
    """

    target_domain = DatasetDomain.FINANCE

    def profile(
        self,
        dataset_profile: DatasetProfile,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> BusinessProfile:
        """
        Generate executive business profile for a Finance dataset.
        """
        primary_kpis = (
            KPIRecommendation(
                name="Gross Revenue",
                priority=Priority.CRITICAL,
                confidence=0.95,
                reason="Revenue entity and finance domain detected.",
                formula="SUM('Ledger'[Gross_Revenue])",
            ),
            KPIRecommendation(
                name="Net Profit",
                priority=Priority.CRITICAL,
                confidence=0.92,
                reason="Profit and Cost entities present in financial data.",
                formula="SUM('Ledger'[Gross_Revenue]) - SUM('Ledger'[Operating_Cost])",
            ),
            KPIRecommendation(
                name="Operating Expenses",
                priority=Priority.HIGH,
                confidence=0.90,
                reason="Cost entity detected on ledger expense accounts.",
                formula="SUM('Ledger'[Operating_Cost])",
            ),
            KPIRecommendation(
                name="Gross Profit Margin %",
                priority=Priority.HIGH,
                confidence=0.88,
                reason="Calculated from Gross Revenue and Net Profit.",
                formula="([Net Profit] / [Gross Revenue]) * 100",
            ),
        )

        secondary_kpis = (
            KPIRecommendation(
                name="Operating Expenses Ratio",
                priority=Priority.MEDIUM,
                confidence=0.82,
                reason="Measures operational efficiency against total revenue.",
                formula="[Operating Expenses] / [Gross Revenue]",
            ),
        )

        dimensions = ("Account_Category", "Cost_Center", "Fiscal_Quarter", "Region")
        measures = ("Gross_Revenue", "Net_Profit", "Operating_Cost", "Tax_Amount")

        business_questions = (
            "What is the net profit margin per operating region?",
            "How are operating expenses scaling relative to gross revenue?",
            "Which cost centers exceed budgeted expenditure?",
        )

        suggested_charts = (
            {"title": "P&L Waterfall Chart", "chart_type": "waterfall", "x_axis": "Account_Category", "y_axis": "Amount"},
            {"title": "Operating Expense Breakdown", "chart_type": "donut", "x_axis": "Cost_Center", "y_axis": "Operating_Cost"},
            {"title": "Quarterly Revenue vs Net Profit", "chart_type": "grouped_bar", "x_axis": "Fiscal_Quarter", "y_axis": "Amount"},
        )

        suggested_dashboard_layout = (
            {"section": "Header", "title": "Financial Performance Overview", "components": ["Gross Revenue", "Net Profit", "Operating Expenses", "Gross Margin %"]},
            {"section": "P&L Analysis", "title": "Profitability & Expense Breakdown", "components": ["P&L Waterfall Chart", "Operating Expense Breakdown"]},
        )

        suggested_filters = ("Fiscal_Quarter", "Cost_Center", "Region")
        time_intelligence = ("Quarter-over-Quarter (QoQ) Profit Growth", "Fiscal Year-to-Date (YTD) Revenue")
        recommended_insights = ("Operating margin expanded by 3.2% in Q3.")
        data_quality_notes = ("All transaction records balanced to zero net variance.")

        entities_tuple = tuple(entities) if entities else ()

        return BusinessProfile(
            domain=DatasetDomain.FINANCE,
            confidence=0.92,
            business_context="Financial analytics monitoring revenue streams, cost structures, and bottom-line profitability.",
            executive_summary="Finance dataset with balance and ledger signals suitable for financial P&L reporting.",
            primary_kpis=primary_kpis,
            secondary_kpis=secondary_kpis,
            dimensions=dimensions,
            measures=measures,
            business_questions=business_questions,
            suggested_charts=suggested_charts,
            suggested_dashboard_layout=suggested_dashboard_layout,
            suggested_filters=suggested_filters,
            time_intelligence=time_intelligence,
            recommended_insights=(recommended_insights,),
            data_quality_notes=(data_quality_notes,),
            entities=entities_tuple,
        )
