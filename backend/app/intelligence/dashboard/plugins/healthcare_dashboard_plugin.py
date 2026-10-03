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
    title='Healthcare Clinical Command Center',
    description='Multi-tab clinical operations dashboard tracking admission volume, length of stay, and treatment expenses.',
    domain=DatasetDomain.HEALTHCARE,
    roles={
        "patient": Role("identifier", keywords=("patient", "admission", "encounter",)),
        "cost": Role("measure", keywords=("treatment", "charge", "bill", "cost",), semantic=SemanticType.COST),
        "stay": Role("measure", keywords=("length_of_stay", "stay", "los",)),
        "date": Role("date", keywords=("admission", "date",)),
        "diagnosis": Role("dimension", keywords=("diagnosis", "condition", "procedure",)),
        "ward": Role("dimension", keywords=("ward", "department", "unit", "hospital",)),
    },
    tabs=(
        TabSpec("tab_clinical", "Clinical Operations", "Patient admission volumes, length of stay, and treatment costs.", kpi_cards=True, charts=(
                ChartSpec("w_diag_cost", "{metric} by {dimension}", "BAR_CHART", "cost", dimension="diagnosis", chart_type="bar", width=8, height=4),
                ChartSpec("w_ward_admissions", "Admissions by {dimension}", "PIE_CHART", "patient", dimension="ward", chart_type="pie", width=4, height=4),
        )),
    ),
    filters=('date', 'diagnosis', 'ward'),
)


class HealthcareDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the HEALTHCARE domain.

    Widgets are described by role and instantiated against the columns the
    dataset really has; a widget whose columns are absent is left out.
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
        return build_dashboard(dataset_profile, kpi_report, SPEC)
