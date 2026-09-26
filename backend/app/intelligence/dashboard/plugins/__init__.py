"""
Dashboard Recommendation plugin registry.

Exports all concrete dashboard plugin classes and the canonical priority registry.
"""

from app.intelligence.dashboard.base_dashboard_plugin import BaseDashboardPlugin
from app.intelligence.dashboard.plugins.fallback_dashboard_plugin import FallbackDashboardPlugin
from app.intelligence.dashboard.plugins.finance_dashboard_plugin import FinanceDashboardPlugin
from app.intelligence.dashboard.plugins.healthcare_dashboard_plugin import HealthcareDashboardPlugin
from app.intelligence.dashboard.plugins.hr_dashboard_plugin import HRDashboardPlugin
from app.intelligence.dashboard.plugins.logistics_dashboard_plugin import LogisticsDashboardPlugin
from app.intelligence.dashboard.plugins.marketing_dashboard_plugin import MarketingDashboardPlugin
from app.intelligence.dashboard.plugins.retail_dashboard_plugin import RetailDashboardPlugin

DASHBOARD_RECOMMENDATION_REGISTRY: tuple[type[BaseDashboardPlugin], ...] = (
    RetailDashboardPlugin,
    FinanceDashboardPlugin,
    HRDashboardPlugin,
    HealthcareDashboardPlugin,
    MarketingDashboardPlugin,
    LogisticsDashboardPlugin,
    FallbackDashboardPlugin,
)

__all__ = [
    "BaseDashboardPlugin",
    "RetailDashboardPlugin",
    "FinanceDashboardPlugin",
    "HRDashboardPlugin",
    "HealthcareDashboardPlugin",
    "MarketingDashboardPlugin",
    "LogisticsDashboardPlugin",
    "FallbackDashboardPlugin",
    "DASHBOARD_RECOMMENDATION_REGISTRY",
]
