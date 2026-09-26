"""
KPI Recommendation plugin registry.

Exports all concrete KPI plugin classes and the canonical priority registry.
"""

from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.plugins.fallback_kpi_plugin import FallbackKPIPlugin
from app.intelligence.kpi.plugins.finance_kpi_plugin import FinanceKPIPlugin
from app.intelligence.kpi.plugins.healthcare_kpi_plugin import HealthcareKPIPlugin
from app.intelligence.kpi.plugins.hr_kpi_plugin import HRKPIPlugin
from app.intelligence.kpi.plugins.logistics_kpi_plugin import LogisticsKPIPlugin
from app.intelligence.kpi.plugins.marketing_kpi_plugin import MarketingKPIPlugin
from app.intelligence.kpi.plugins.retail_kpi_plugin import RetailKPIPlugin

KPI_RECOMMENDATION_REGISTRY: tuple[type[BaseKPIPlugin], ...] = (
    RetailKPIPlugin,
    FinanceKPIPlugin,
    HRKPIPlugin,
    HealthcareKPIPlugin,
    MarketingKPIPlugin,
    LogisticsKPIPlugin,
    FallbackKPIPlugin,
)

__all__ = [
    "BaseKPIPlugin",
    "RetailKPIPlugin",
    "FinanceKPIPlugin",
    "HRKPIPlugin",
    "HealthcareKPIPlugin",
    "MarketingKPIPlugin",
    "LogisticsKPIPlugin",
    "FallbackKPIPlugin",
    "KPI_RECOMMENDATION_REGISTRY",
]
