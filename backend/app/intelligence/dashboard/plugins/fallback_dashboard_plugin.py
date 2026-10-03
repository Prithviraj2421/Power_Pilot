from typing import Optional

from app.common.enums import DatasetDomain
from app.intelligence.dashboard.base_dashboard_plugin import BaseDashboardPlugin
from app.intelligence.dashboard.builder import flow, kpi_cards, pretty
from app.intelligence.kpi.column_resolver import ColumnResolver
from app.models.business_profile import BusinessProfile
from app.models.dashboard_models import DashboardRecommendationReport, DashboardTab, WidgetConfig
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import InsightReport
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport

_GRAINS = ("Year", "Quarter", "Month")
_MAX_FILTER_VALUES = 50


class FallbackDashboardPlugin(BaseDashboardPlugin):
    """
    Dashboard for UNKNOWN or unclassified domains, built only from columns the dataset has.

    Identifier and code columns are never charted as measures, and no chart is
    drawn when the dataset lacks the columns it would need.
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
        resolver = ColumnResolver(dataset_profile)
        measures = resolver.measures()
        dimensions = resolver.dimensions()
        date_column = resolver.date()
        metric = measures[0] if measures else None
        dimension = dimensions[0] if dimensions else None

        charts: list[WidgetConfig] = []
        if metric and dimension:
            charts.append(
                WidgetConfig(
                    widget_id="w_gen_bar",
                    title=f"{pretty(metric)} by {pretty(dimension)}",
                    widget_type="BAR_CHART",
                    metric_column=metric,
                    dimension_column=dimension,
                    chart_type="bar",
                    grid_width=12,
                )
            )
        if metric and date_column:
            charts.append(
                WidgetConfig(
                    widget_id="w_gen_trend",
                    title=f"{pretty(metric)} Trend",
                    widget_type="LINE_CHART",
                    metric_column=metric,
                    dimension_column=date_column,
                    chart_type="line",
                    grid_width=12,
                )
            )

        cards = kpi_cards(kpi_report)
        widgets = cards + flow(charts, first_row=2 if cards else 1)
        tabs = (
            (
                DashboardTab(
                    tab_id="tab_exploratory",
                    tab_name="General Exploratory BI",
                    description="Exploratory metric aggregations and dimension breakdowns.",
                    widgets=tuple(widgets),
                ),
            )
            if widgets
            else ()
        )

        # A filter on a column with thousands of distinct values is unusable, so prefer low-cardinality ones.
        profiles = {c.name: c for c in dataset_profile.columns}
        usable = [d for d in dimensions if 1 < profiles[d].unique_count <= _MAX_FILTER_VALUES]

        return DashboardRecommendationReport(
            dashboard_title=f"General BI Dashboard — {dataset_profile.dataset_name}",
            description="Exploratory dashboard layout for unclassified dataset.",
            domain=DatasetDomain.UNKNOWN,
            tabs=tabs,
            global_filters=tuple((usable or dimensions)[:3]),
            time_intelligence_dimensions=(date_column, *_GRAINS) if date_column else (),
        )
