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
    title='Financial P&L Executive Command Center',
    description='Multi-tab financial BI dashboard for FP&A ledger monitoring and EBITDA margin analysis.',
    domain=DatasetDomain.FINANCE,
    roles={
        "revenue": Role("measure", keywords=("revenue", "income", "turnover", "sales", "amount",), semantic=SemanticType.REVENUE),
        "expense": Role("measure", keywords=("expense", "expenses", "opex", "cost", "cogs",), semantic=SemanticType.COST),
        "date": Role("date", keywords=("posting", "date", "period",)),
        "account": Role("dimension", keywords=("account", "ledger", "category",)),
        "department": Role("dimension", keywords=("department", "division", "unit", "entity",)),
        "cost_center": Role("dimension", keywords=("cost_center", "center",)),
    },
    tabs=(
        TabSpec("tab_pnl", "Executive P&L Overview", "P&L financial metrics, revenue, and operating profit.", kpi_cards=True, charts=(
                ChartSpec("w_rev_account", "{metric} by {dimension}", "BAR_CHART", "revenue", dimension="account", chart_type="bar", width=8, height=4),
                ChartSpec("w_exp_pie", "{metric} by {dimension}", "PIE_CHART", "expense", dimension="department", chart_type="pie", width=4, height=4),
        )),
    ),
    filters=('date', 'department', 'cost_center'),
)


class FinanceDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the FINANCE domain.

    Widgets are described by role and instantiated against the columns the
    dataset really has; a widget whose columns are absent is left out.
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
        return build_dashboard(dataset_profile, kpi_report, SPEC)
