from typing import Optional

from app.common.enums import DatasetDomain, PhysicalType
from app.intelligence.dashboard.base_dashboard_plugin import BaseDashboardPlugin
from app.models.business_profile import BusinessProfile
from app.models.dashboard_models import DashboardRecommendationReport, DashboardTab, WidgetConfig
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import InsightReport
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport


class FallbackDashboardPlugin(BaseDashboardPlugin):
    """
    Fallback dashboard recommendation plugin for UNKNOWN or unclassified domains.
    """

    target_domain = DatasetDomain.UNKNOWN

    def recommend(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        insight_report: Optional[InsightReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        kpi_report: Optional[KPIReport] = None,
    ) -> DashboardRecommendationReport:
        num_cols = [c.name for c in dataset_profile.columns if c.physical_type in (PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.DECIMAL)]
        cat_cols = [c.name for c in dataset_profile.columns if c.physical_type in (PhysicalType.CATEGORICAL, PhysicalType.TEXT)]
        date_cols = [c.name for c in dataset_profile.columns if c.physical_type in (PhysicalType.DATE, PhysicalType.DATETIME)]

        metric_col = num_cols[0] if num_cols else "Record_Count"
        dim_col = cat_cols[0] if cat_cols else "Index"

        t1_widgets = (
            WidgetConfig(widget_id="w_gen_kpi", title=f"Total {metric_col.replace('_', ' ').title()}", widget_type="KPI_CARD", metric_column=metric_col, grid_row=1, grid_col=1, grid_width=6, grid_height=2),
            WidgetConfig(widget_id="w_gen_count", title="Total Rows", widget_type="KPI_CARD", metric_column="Row_Count", grid_row=1, grid_col=7, grid_width=6, grid_height=2),
            WidgetConfig(widget_id="w_gen_bar", title=f"{metric_col.replace('_', ' ').title()} by {dim_col.replace('_', ' ').title()}", widget_type="BAR_CHART", metric_column=metric_col, dimension_column=dim_col, chart_type="bar", grid_row=2, grid_col=1, grid_width=12, grid_height=4),
        )
        tab1 = DashboardTab(tab_id="tab_exploratory", tab_name="General Exploratory BI", description="Exploratory metric aggregations and dimension breakdowns.", widgets=t1_widgets)

        return DashboardRecommendationReport(
            dashboard_title=f"General BI Dashboard — {dataset_profile.dataset_name}",
            description="Exploratory dashboard layout for unclassified dataset.",
            domain=DatasetDomain.UNKNOWN,
            tabs=(tab1,),
            global_filters=tuple(cat_cols[:3]),
            time_intelligence_dimensions=tuple(date_cols),
        )
