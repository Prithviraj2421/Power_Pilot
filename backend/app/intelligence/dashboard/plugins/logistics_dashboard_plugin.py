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
    title='Supply Chain & Freight Logistics Command Center',
    description='Multi-tab supply chain BI dashboard monitoring carrier SLAs, shipment volume, and freight spend.',
    domain=DatasetDomain.LOGISTICS,
    roles={
        "freight": Role("measure", keywords=("freight", "shipping_cost", "shipping", "cost",), semantic=SemanticType.COST),
        "delay": Role("measure", keywords=("delay", "late",)),
        "date": Role("date", keywords=("ship", "delivery", "date",)),
        "carrier": Role("dimension", keywords=("carrier", "shipper", "vendor", "mode",)),
        "destination": Role("dimension", keywords=("destination", "region", "country",)),
        "origin": Role("dimension", keywords=("origin", "warehouse", "depot",)),
    },
    tabs=(
        TabSpec("tab_supply_chain", "Supply Chain Command Center", "Logistics shipping volume, carrier delay days, and freight costs.", kpi_cards=True, charts=(
                ChartSpec("w_carrier_cost", "{metric} by {dimension}", "BAR_CHART", "freight", dimension="carrier", chart_type="bar", width=6, height=4),
                ChartSpec("w_delay_region", "{metric} by {dimension}", "BAR_CHART", "delay", dimension="destination", chart_type="bar", width=6, height=4),
        )),
    ),
    filters=('carrier', 'destination', 'origin', 'date'),
)


class LogisticsDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard recommendation plugin for the LOGISTICS domain.

    Widgets are described by role and instantiated against the columns the
    dataset really has; a widget whose columns are absent is left out.
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
        return build_dashboard(dataset_profile, kpi_report, SPEC)
