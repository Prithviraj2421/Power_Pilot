from typing import Optional

from app.common.enums import DatasetDomain
from app.intelligence.dashboard.base_dashboard_plugin import BaseDashboardPlugin
from app.models.business_profile import BusinessProfile
from app.models.dashboard_models import DashboardRecommendationReport, DashboardTab, WidgetConfig
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import InsightReport
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport


class FinanceDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the FINANCE domain.
    """

    target_domain = DatasetDomain.FINANCE

    def recommend(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        insight_report: Optional[InsightReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        kpi_report: Optional[KPIReport] = None,
    ) -> DashboardRecommendationReport:
        t1_widgets = (
            WidgetConfig(widget_id="w_gross_rev", title="Gross Revenue", widget_type="KPI_CARD", metric_column="Gross_Revenue", grid_row=1, grid_col=1, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_ebitda", title="Net EBITDA Profit", widget_type="KPI_CARD", metric_column="EBITDA", grid_row=1, grid_col=5, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_opex_ratio", title="Operating Expense Ratio", widget_type="KPI_CARD", metric_column="Opex_Ratio", grid_row=1, grid_col=9, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_waterfall", title="P&L EBITDA Waterfall Breakdown", widget_type="BAR_CHART", metric_column="Amount", dimension_column="Ledger_Account", chart_type="waterfall", grid_row=2, grid_col=1, grid_width=8, grid_height=4),
            WidgetConfig(widget_id="w_exp_pie", title="Operating Expenses by Department", widget_type="PIE_CHART", metric_column="Operating_Expenses", dimension_column="Department", chart_type="pie", grid_row=2, grid_col=9, grid_width=4, grid_height=4),
        )
        tab1 = DashboardTab(tab_id="tab_pnl", tab_name="Executive P&L Overview", description="P&L financial metrics, revenue, and operating profit.", widgets=t1_widgets)

        return DashboardRecommendationReport(
            dashboard_title="Financial P&L Executive Command Center",
            description="Multi-tab financial BI dashboard for FP&A ledger monitoring and EBITDA margin analysis.",
            domain=DatasetDomain.FINANCE,
            tabs=(tab1,),
            global_filters=("Fiscal_Period", "Department", "Cost_Center", "Entity"),
            time_intelligence_dimensions=("Posting_Date", "Fiscal_Year", "Fiscal_Quarter"),
        )
