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


class MarketingDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the MARKETING domain.
    """

    target_domain = DatasetDomain.MARKETING

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
            WidgetConfig(widget_id="w_roas", title="Return on Ad Spend (ROAS)", widget_type="KPI_CARD", metric_column="ROAS", grid_row=1, grid_col=1, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_cpa", title="Cost Per Acquisition (CPA)", widget_type="KPI_CARD", metric_column="CPA", grid_row=1, grid_col=5, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_spend", title="Total Ad Spend", widget_type="KPI_CARD", metric_column="Ad_Spend", grid_row=1, grid_col=9, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_chan_roas", title="ROAS by Marketing Channel", widget_type="BAR_CHART", metric_column="Revenue", dimension_column="Marketing_Channel", chart_type="bar", grid_row=2, grid_col=1, grid_width=6, grid_height=4),
            WidgetConfig(widget_id="w_conv_funnel", title="Conversions by Campaign", widget_type="BAR_CHART", metric_column="Conversions", dimension_column="Campaign_Name", chart_type="horizontal_bar", grid_row=2, grid_col=7, grid_width=6, grid_height=4),
        )
        tab1 = DashboardTab(tab_id="tab_mkt_exec", tab_name="Campaign Performance", description="Ad spend efficiency, ROAS, and channel conversions.", widgets=t1_widgets)

        return DashboardRecommendationReport(
            dashboard_title="Marketing Campaign ROAS & Conversion Dashboard",
            description="Multi-tab marketing BI dashboard tracking ad spend efficiency, ROAS, and lead conversions.",
            domain=DatasetDomain.MARKETING,
            tabs=(tab1,),
            global_filters=("Campaign_Name", "Marketing_Channel", "Ad_Medium", "Click_Date"),
            time_intelligence_dimensions=("Click_Date", "Year", "Month", "Week"),
        )
