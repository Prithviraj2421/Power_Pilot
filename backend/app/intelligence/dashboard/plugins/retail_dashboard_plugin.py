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


class RetailDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the RETAIL domain.
    """

    target_domain = DatasetDomain.RETAIL

    def recommend(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        insight_report: Optional[InsightReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        kpi_report: Optional[KPIReport] = None,
    ) -> DashboardRecommendationReport:
        # Tab 1: Executive Overview
        t1_widgets = (
            WidgetConfig(widget_id="w_kpi_rev", title="Total Sales Revenue", widget_type="KPI_CARD", metric_column="Sales_Amount", grid_row=1, grid_col=1, grid_width=3, grid_height=2),
            WidgetConfig(widget_id="w_kpi_aov", title="Average Order Value (AOV)", widget_type="KPI_CARD", metric_column="AOV", grid_row=1, grid_col=4, grid_width=3, grid_height=2),
            WidgetConfig(widget_id="w_kpi_units", title="Total Units Sold", widget_type="KPI_CARD", metric_column="Quantity", grid_row=1, grid_col=7, grid_width=3, grid_height=2),
            WidgetConfig(widget_id="w_kpi_cust", title="Active Customers", widget_type="KPI_CARD", metric_column="Customer_ID", grid_row=1, grid_col=10, grid_width=3, grid_height=2),
            WidgetConfig(widget_id="w_trend_rev", title="Sales Revenue Growth Trend", widget_type="LINE_CHART", metric_column="Sales_Amount", dimension_column="Order_Date", chart_type="line", grid_row=2, grid_col=1, grid_width=8, grid_height=4),
            WidgetConfig(widget_id="w_cat_breakdown", title="Sales by Product Category", widget_type="BAR_CHART", metric_column="Sales_Amount", dimension_column="Category", chart_type="bar", grid_row=2, grid_col=9, grid_width=4, grid_height=4),
        )
        tab1 = DashboardTab(tab_id="tab_exec", tab_name="Executive Summary", description="Core retail sales scorecards and revenue trends.", widgets=t1_widgets)

        # Tab 2: Sales & Product Analytics
        t2_widgets = (
            WidgetConfig(widget_id="w_top_products", title="Top 10 Revenue Products", widget_type="BAR_CHART", metric_column="Sales_Amount", dimension_column="Product_Name", chart_type="horizontal_bar", grid_row=1, grid_col=1, grid_width=6, grid_height=4),
            WidgetConfig(widget_id="w_qty_vs_rev", title="Quantity Sold vs Revenue Correlation", widget_type="SCATTER_PLOT", metric_column="Sales_Amount", dimension_column="Quantity", chart_type="scatter", grid_row=1, grid_col=7, grid_width=6, grid_height=4),
            WidgetConfig(widget_id="w_prod_table", title="Product Performance Matrix", widget_type="TABLE", metric_column="Sales_Amount", dimension_column="Product_ID", grid_row=2, grid_col=1, grid_width=12, grid_height=4),
        )
        tab2 = DashboardTab(tab_id="tab_product", tab_name="Product Analytics", description="Product revenue concentration and basket analysis.", widgets=t2_widgets)

        return DashboardRecommendationReport(
            dashboard_title="Retail Operations Executive Dashboard",
            description="Multi-tab interactive BI dashboard for monitoring retail revenue, AOV, and product basket performance.",
            domain=DatasetDomain.RETAIL,
            tabs=(tab1, tab2),
            global_filters=("Order_Date", "Category", "Region", "Store_ID"),
            time_intelligence_dimensions=("Order_Date", "Year", "Quarter", "Month"),
        )
