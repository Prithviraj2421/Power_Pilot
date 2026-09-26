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


class HealthcareDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the HEALTHCARE domain.
    """

    target_domain = DatasetDomain.HEALTHCARE

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
            WidgetConfig(widget_id="w_admissions", title="Total Patient Admissions", widget_type="KPI_CARD", metric_column="Patient_ID", grid_row=1, grid_col=1, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_alos", title="Average Length of Stay (ALOS)", widget_type="KPI_CARD", metric_column="Length_Of_Stay_Days", grid_row=1, grid_col=5, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_treat_cost", title="Total Treatment Spend", widget_type="KPI_CARD", metric_column="Treatment_Cost", grid_row=1, grid_col=9, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_diag_cost", title="Treatment Cost by Diagnosis", widget_type="BAR_CHART", metric_column="Treatment_Cost", dimension_column="Diagnosis", chart_type="bar", grid_row=2, grid_col=1, grid_width=8, grid_height=4),
            WidgetConfig(widget_id="w_hosp_breakdown", title="Admissions by Hospital Ward", widget_type="PIE_CHART", metric_column="Patient_ID", dimension_column="Ward", chart_type="pie", grid_row=2, grid_col=9, grid_width=4, grid_height=4),
        )
        tab1 = DashboardTab(tab_id="tab_clinical", tab_name="Clinical Operations", description="Patient admission volumes, length of stay, and treatment costs.", widgets=t1_widgets)

        return DashboardRecommendationReport(
            dashboard_title="Healthcare Clinical Command Center",
            description="Multi-tab clinical operations dashboard tracking admission volume, length of stay, and treatment expenses.",
            domain=DatasetDomain.HEALTHCARE,
            tabs=(tab1,),
            global_filters=("Admission_Date", "Diagnosis", "Ward", "Physician"),
            time_intelligence_dimensions=("Admission_Date", "Year", "Month"),
        )
