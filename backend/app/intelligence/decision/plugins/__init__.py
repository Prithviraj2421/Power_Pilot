"""
Decision Engine plugin registry.

Exports all concrete decision plugin classes and the canonical priority registry.
"""

from app.intelligence.decision.base_decision_plugin import BaseDecisionPlugin
from app.intelligence.decision.plugins.fallback_decision_plugin import FallbackDecisionPlugin
from app.intelligence.decision.plugins.finance_decision_plugin import FinanceDecisionPlugin
from app.intelligence.decision.plugins.healthcare_decision_plugin import HealthcareDecisionPlugin
from app.intelligence.decision.plugins.hr_decision_plugin import HRDecisionPlugin
from app.intelligence.decision.plugins.logistics_decision_plugin import LogisticsDecisionPlugin
from app.intelligence.decision.plugins.marketing_decision_plugin import MarketingDecisionPlugin
from app.intelligence.decision.plugins.retail_decision_plugin import RetailDecisionPlugin

DECISION_ENGINE_REGISTRY: tuple[type[BaseDecisionPlugin], ...] = (
    RetailDecisionPlugin,
    FinanceDecisionPlugin,
    HRDecisionPlugin,
    HealthcareDecisionPlugin,
    MarketingDecisionPlugin,
    LogisticsDecisionPlugin,
    FallbackDecisionPlugin,
)

__all__ = [
    "BaseDecisionPlugin",
    "RetailDecisionPlugin",
    "FinanceDecisionPlugin",
    "HRDecisionPlugin",
    "HealthcareDecisionPlugin",
    "MarketingDecisionPlugin",
    "LogisticsDecisionPlugin",
    "FallbackDecisionPlugin",
    "DECISION_ENGINE_REGISTRY",
]
