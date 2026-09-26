from dataclasses import dataclass, field
from typing import Optional

from app.common.enums import DatasetDomain


@dataclass(slots=True, frozen=True)
class WidgetConfig:
    """
    Immutable representation of a visual dashboard widget configuration.
    """

    widget_id: str
    title: str
    widget_type: str  # 'KPI_CARD', 'BAR_CHART', 'LINE_CHART', 'SCATTER_PLOT', 'PIE_CHART', 'TABLE', 'FILTER_PANEL'
    metric_column: Optional[str] = None
    dimension_column: Optional[str] = None
    chart_type: Optional[str] = None
    grid_row: int = 1
    grid_col: int = 1
    grid_width: int = 4
    grid_height: int = 3
    options: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DashboardTab:
    """
    Immutable representation of a dashboard tab containing a grid of widgets.
    """

    tab_id: str
    tab_name: str
    description: str
    widgets: tuple[WidgetConfig, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class DashboardRecommendationReport:
    """
    Unified immutable report containing multi-tab dashboard layout recommendations.
    """

    dashboard_title: str
    description: str
    domain: DatasetDomain = DatasetDomain.UNKNOWN
    tabs: tuple[DashboardTab, ...] = field(default_factory=tuple)
    global_filters: tuple[str, ...] = field(default_factory=tuple)
    time_intelligence_dimensions: tuple[str, ...] = field(default_factory=tuple)
