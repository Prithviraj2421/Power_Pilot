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
    title='Retail Operations Executive Dashboard',
    description='Multi-tab interactive BI dashboard for monitoring retail revenue, AOV, and product basket performance.',
    domain=DatasetDomain.RETAIL,
    roles={
        "revenue": Role("measure", keywords=("sales", "revenue", "turnover", "total_amount", "amount",), semantic=SemanticType.REVENUE),
        "quantity": Role("measure", keywords=("quantity", "qty", "units",), semantic=SemanticType.QUANTITY),
        "date": Role("date", keywords=("order", "date",)),
        "category": Role("dimension", keywords=("category", "segment", "type", "class", "department",)),
        "product": Role("dimension", keywords=("product", "item", "sku",)),
        "region": Role("dimension", keywords=("region", "state", "country", "city",), semantic=SemanticType.REGION),
    },
    tabs=(
        TabSpec("tab_exec", "Executive Summary", "Core retail sales scorecards and revenue trends.", kpi_cards=True, charts=(
                ChartSpec("w_trend_rev", "{metric} Trend", "LINE_CHART", "revenue", dimension="date", chart_type="line", width=8, height=4),
                ChartSpec("w_cat_breakdown", "{metric} by {dimension}", "BAR_CHART", "revenue", dimension="category", chart_type="bar", width=4, height=4),
        )),
        TabSpec("tab_product", "Product Analytics", "Product revenue concentration and basket analysis.", charts=(
                ChartSpec("w_top_products", "{metric} by {dimension}", "BAR_CHART", "revenue", dimension="product", chart_type="horizontal_bar", width=6, height=4),
                ChartSpec("w_qty_vs_rev", "{dimension} vs {metric}", "SCATTER_PLOT", "revenue", dimension="quantity", chart_type="scatter", width=6, height=4),
                ChartSpec("w_prod_table", "{metric} by {dimension}", "TABLE", "revenue", dimension="product", width=12, height=4),
        )),
    ),
    filters=('date', 'category', 'region'),
)


class RetailDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the RETAIL domain.

    Widgets are described by role and instantiated against the columns the
    dataset really has; a widget whose columns are absent is left out.
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
        return build_dashboard(dataset_profile, kpi_report, SPEC)
