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


class LogisticsDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the LOGISTICS domain.
    """

    target_domain = DatasetDomain.LOGISTICS

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
            WidgetConfig(widget_id="w_freight_cost", title="Total Freight Spend", widget_type="KPI_CARD", metric_column="Freight_Cost", grid_row=1, grid_col=1, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_delay_days", title="Average Shipping Delay (Days)", widget_type="KPI_CARD", metric_column="Delay_Days", grid_row=1, grid_col=5, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_volume", title="Total Shipped Volume", widget_type="KPI_CARD", metric_column="Quantity_Shipped", grid_row=1, grid_col=9, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_carrier_cost", title="Freight Spend by Carrier", widget_type="BAR_CHART", metric_column="Freight_Cost", dimension_column="Carrier", chart_type="bar", grid_row=2, grid_col=1, grid_width=6, grid_height=4),
            WidgetConfig(widget_id="w_delay_region", title="Shipping Delay by Destination Region", widget_type="BAR_CHART", metric_column="Delay_Days", dimension_column="Destination_Region", chart_type="bar", grid_row=2, grid_col=7, grid_width=6, grid_height=4),
        )
        tab1 = DashboardTab(tab_id="tab_supply_chain", tab_name="Supply Chain Command Center", description="Logistics shipping volume, carrier delay days, and freight costs.", widgets=t1_widgets)

        return DashboardRecommendationReport(
            dashboard_title="Supply Chain & Freight Logistics Command Center",
            description="Multi-tab supply chain BI dashboard monitoring carrier SLAs, shipment volume, and freight spend.",
            domain=DatasetDomain.LOGISTICS,
            tabs=(tab1,),
            global_filters=("Carrier", "Destination_Region", "Origin_Warehouse", "Shipment_Date"),
            time_intelligence_dimensions=("Shipment_Date", "Year", "Month"),
        )
