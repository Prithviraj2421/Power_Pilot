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


class HRDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the HR domain.
    """

    target_domain = DatasetDomain.HR

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
            WidgetConfig(widget_id="w_headcount", title="Total Active Headcount", widget_type="KPI_CARD", metric_column="Employee_ID", grid_row=1, grid_col=1, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_payroll", title="Total Payroll Spend", widget_type="KPI_CARD", metric_column="Salary", grid_row=1, grid_col=5, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_tenure", title="Average Tenure (Years)", widget_type="KPI_CARD", metric_column="Tenure_Years", grid_row=1, grid_col=9, grid_width=4, grid_height=2),
            WidgetConfig(widget_id="w_dept_headcount", title="Headcount by Department", widget_type="BAR_CHART", metric_column="Employee_ID", dimension_column="Department", chart_type="bar", grid_row=2, grid_col=1, grid_width=6, grid_height=4),
            WidgetConfig(widget_id="w_salary_dist", title="Salary Distribution by Department", widget_type="BAR_CHART", metric_column="Salary", dimension_column="Department", chart_type="stacked_bar", grid_row=2, grid_col=7, grid_width=6, grid_height=4),
        )
        tab1 = DashboardTab(tab_id="tab_hr_exec", tab_name="Workforce Overview", description="Human capital headcount, payroll, and tenure metrics.", widgets=t1_widgets)

        return DashboardRecommendationReport(
            dashboard_title="HR Executive Workforce Dashboard",
            description="Multi-tab HR analytics dashboard tracking headcount growth, salary equity, and departmental tenure.",
            domain=DatasetDomain.HR,
            tabs=(tab1,),
            global_filters=("Department", "Job_Level", "Location", "Hire_Date"),
            time_intelligence_dimensions=("Hire_Date", "Year", "Quarter"),
        )
