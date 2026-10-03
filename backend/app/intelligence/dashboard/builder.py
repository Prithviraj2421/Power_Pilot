from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.common.enums import DatasetDomain, SemanticType
from app.common.powerbi_names import dax_references
from app.intelligence.kpi.column_resolver import ColumnResolver
from app.models.dashboard_models import DashboardRecommendationReport, DashboardTab, WidgetConfig
from app.models.dataset_profile import DatasetProfile
from app.models.kpi_report import KPIReport

_GRID_COLUMNS = 12
_GRAINS = ("Year", "Quarter", "Month")


@dataclass(frozen=True)
class Role:
    """How to find one business role in a dataset: by detected entity type, then by name."""

    kind: str  # "measure" | "dimension" | "identifier" | "date"
    keywords: tuple[str, ...] = ()
    semantic: Optional[SemanticType] = None


@dataclass(frozen=True)
class ChartSpec:
    """A chart described in terms of roles. Titles may use {metric} and {dimension}."""

    widget_id: str
    title: str
    widget_type: str
    metric: str
    dimension: Optional[str] = None
    chart_type: Optional[str] = None
    width: int = 6
    height: int = 4


@dataclass(frozen=True)
class TabSpec:
    tab_id: str
    name: str
    description: str
    charts: tuple[ChartSpec, ...]
    kpi_cards: bool = False


@dataclass(frozen=True)
class DashboardSpec:
    title: str
    description: str
    domain: DatasetDomain
    roles: dict[str, Role]
    tabs: tuple[TabSpec, ...]
    filters: tuple[str, ...] = ()


def pretty(column: str) -> str:
    return column.replace("_", " ").strip().title()


def _resolve(resolver: ColumnResolver, roles: dict[str, Role]) -> dict[str, Optional[str]]:
    found: dict[str, Optional[str]] = {}
    for name, role in roles.items():
        if role.kind == "measure":
            found[name] = resolver.measure(role.semantic, role.keywords)
        elif role.kind == "identifier":
            found[name] = resolver.identifier(role.semantic, role.keywords)
        elif role.kind == "date":
            found[name] = resolver.date(role.keywords)
        else:
            found[name] = resolver.dimension(role.semantic, role.keywords)
    return found


def kpi_cards(kpi_report: Optional[KPIReport]) -> list[WidgetConfig]:
    """One card per primary KPI, so the dashboard and the KPI tab can never disagree."""
    if kpi_report is None:
        return []
    kpis = list(kpi_report.primary_kpis)
    if not kpis:
        return []
    width = _GRID_COLUMNS // min(len(kpis), 4)
    cards = []
    for index, kpi in enumerate(kpis[:4]):
        refs = dax_references(kpi.formula) if kpi.formula else []
        cards.append(
            WidgetConfig(
                widget_id=f"w_kpi_{index + 1}",
                title=kpi.name,
                widget_type="KPI_CARD",
                metric_column=refs[0][1] if refs else None,
                grid_row=1,
                grid_col=1 + index * width,
                grid_width=width,
                grid_height=2,
            )
        )
    return cards


def flow(charts: list[WidgetConfig], first_row: int) -> list[WidgetConfig]:
    """Re-place charts left to right on the 12-column grid, so dropped widgets leave no gaps."""
    placed, row, col = [], first_row, 1
    for chart in charts:
        if col > 1 and col - 1 + chart.grid_width > _GRID_COLUMNS:
            row, col = row + 1, 1
        placed.append(
            WidgetConfig(
                widget_id=chart.widget_id,
                title=chart.title,
                widget_type=chart.widget_type,
                metric_column=chart.metric_column,
                dimension_column=chart.dimension_column,
                chart_type=chart.chart_type,
                grid_row=row,
                grid_col=col,
                grid_width=chart.grid_width,
                grid_height=chart.grid_height,
                options=chart.options,
            )
        )
        col += chart.grid_width
    return placed


def build_dashboard(
    profile: DatasetProfile, kpi_report: Optional[KPIReport], spec: DashboardSpec
) -> DashboardRecommendationReport:
    """Instantiate a spec against a dataset: only widgets whose columns exist are kept."""
    resolver = ColumnResolver(profile)
    columns = _resolve(resolver, spec.roles)

    tabs: list[DashboardTab] = []
    for tab_spec in spec.tabs:
        cards = kpi_cards(kpi_report) if tab_spec.kpi_cards else []
        charts: list[WidgetConfig] = []
        for chart in tab_spec.charts:
            metric = columns.get(chart.metric)
            dimension = columns.get(chart.dimension) if chart.dimension else None
            if metric is None or (chart.dimension and dimension is None) or metric == dimension:
                continue
            charts.append(
                WidgetConfig(
                    widget_id=chart.widget_id,
                    title=chart.title.format(metric=pretty(metric), dimension=pretty(dimension or "")),
                    widget_type=chart.widget_type,
                    metric_column=metric,
                    dimension_column=dimension,
                    chart_type=chart.chart_type,
                    grid_width=chart.width,
                    grid_height=chart.height,
                )
            )
        widgets = cards + flow(charts, first_row=2 if cards else 1)
        if widgets:
            tabs.append(
                DashboardTab(
                    tab_id=tab_spec.tab_id,
                    tab_name=tab_spec.name,
                    description=tab_spec.description,
                    widgets=tuple(widgets),
                )
            )

    filters = tuple(dict.fromkeys(c for c in (columns.get(f) for f in spec.filters) if c))
    date_column = columns.get("date")
    return DashboardRecommendationReport(
        dashboard_title=spec.title,
        description=spec.description,
        domain=spec.domain,
        tabs=tuple(tabs),
        global_filters=filters,
        time_intelligence_dimensions=(date_column, *_GRAINS) if date_column else (),
    )
