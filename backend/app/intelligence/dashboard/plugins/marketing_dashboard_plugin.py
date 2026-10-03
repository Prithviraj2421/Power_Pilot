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
    title='Marketing Campaign ROAS & Conversion Dashboard',
    description='Multi-tab marketing BI dashboard tracking ad spend efficiency, ROAS, and lead conversions.',
    domain=DatasetDomain.MARKETING,
    roles={
        "revenue": Role("measure", keywords=("revenue", "sales", "income", "amount",), semantic=SemanticType.REVENUE),
        "conversions": Role("measure", keywords=("conversions", "conversion", "leads", "acquisitions",)),
        "date": Role("date", keywords=("click", "date", "day",)),
        "channel": Role("dimension", keywords=("channel", "medium", "source",)),
        "campaign": Role("dimension", keywords=("campaign",)),
    },
    tabs=(
        TabSpec("tab_mkt_exec", "Campaign Performance", "Ad spend efficiency, ROAS, and channel conversions.", kpi_cards=True, charts=(
                ChartSpec("w_chan_revenue", "{metric} by {dimension}", "BAR_CHART", "revenue", dimension="channel", chart_type="bar", width=6, height=4),
                ChartSpec("w_conv_campaign", "{metric} by {dimension}", "BAR_CHART", "conversions", dimension="campaign", chart_type="horizontal_bar", width=6, height=4),
        )),
    ),
    filters=('campaign', 'channel', 'date'),
)


class MarketingDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the MARKETING domain.

    Widgets are described by role and instantiated against the columns the
    dataset really has; a widget whose columns are absent is left out.
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
        return build_dashboard(dataset_profile, kpi_report, SPEC)
