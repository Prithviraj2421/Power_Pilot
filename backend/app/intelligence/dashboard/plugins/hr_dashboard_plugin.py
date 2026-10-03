from typing import Optional

from app.common.enums import DatasetDomain, SemanticType
from app.intelligence.dashboard.base_dashboard_plugin import BaseDashboardPlugin
from app.intelligence.dashboard.builder import ChartSpec, DashboardSpec, Role, TabSpec, build_dashboard
from app.models.business_profile import BusinessProfile
from app.models.dashboard_models import DashboardRecommendationReport
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import InsightReport
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport

SPEC = DashboardSpec(
    title='HR Executive Workforce Dashboard',
    description='Multi-tab HR analytics dashboard tracking headcount growth, salary equity, and departmental tenure.',
    domain=DatasetDomain.HR,
    roles={
        "employee": Role("identifier", keywords=("employee", "emp", "staff",), semantic=SemanticType.EMPLOYEE),
        "salary": Role("measure", keywords=("salary", "wage", "compensation", "pay",)),
        "date": Role("date", keywords=("hire", "joining", "date",)),
        "department": Role("dimension", keywords=("department", "dept", "team", "division",)),
        "level": Role("dimension", keywords=("level", "grade", "job_title", "title", "role",)),
        "location": Role("dimension", keywords=("location", "region", "city", "office",), semantic=SemanticType.REGION),
    },
    tabs=(
        TabSpec("tab_hr_exec", "Workforce Overview", "Human capital headcount, payroll, and tenure metrics.", kpi_cards=True, charts=(
                ChartSpec("w_dept_headcount", "Headcount by {dimension}", "BAR_CHART", "employee", dimension="department", chart_type="bar", width=6, height=4),
                ChartSpec("w_salary_dist", "{metric} by {dimension}", "BAR_CHART", "salary", dimension="department", chart_type="stacked_bar", width=6, height=4),
        )),
    ),
    filters=('department', 'level', 'location', 'date'),
)


class HRDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the HR domain.

    Widgets are described by role and instantiated against the columns the
    dataset really has; a widget whose columns are absent is left out.
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
        return build_dashboard(dataset_profile, kpi_report, SPEC)
