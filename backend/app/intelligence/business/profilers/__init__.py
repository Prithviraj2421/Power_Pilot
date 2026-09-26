"""
Business Intelligence profiler plugin registry.

Exports all concrete business domain profiler classes and the canonical priority registry.
"""

from app.intelligence.business.base_business_profiler import BaseBusinessProfiler
from app.intelligence.business.profilers.fallback_profiler import FallbackProfiler
from app.intelligence.business.profilers.finance_profiler import FinanceProfiler
from app.intelligence.business.profilers.healthcare_profiler import HealthcareProfiler
from app.intelligence.business.profilers.hr_profiler import HRProfiler
from app.intelligence.business.profilers.logistics_profiler import LogisticsProfiler
from app.intelligence.business.profilers.marketing_profiler import MarketingProfiler
from app.intelligence.business.profilers.retail_profiler import RetailProfiler

BUSINESS_PROFILE_REGISTRY: tuple[type[BaseBusinessProfiler], ...] = (
    RetailProfiler,
    FinanceProfiler,
    HRProfiler,
    HealthcareProfiler,
    MarketingProfiler,
    LogisticsProfiler,
    FallbackProfiler,
)

__all__ = [
    "BaseBusinessProfiler",
    "RetailProfiler",
    "FinanceProfiler",
    "HRProfiler",
    "HealthcareProfiler",
    "MarketingProfiler",
    "LogisticsProfiler",
    "FallbackProfiler",
    "BUSINESS_PROFILE_REGISTRY",
]
