"""
Insight Generator plugin registry.

Exports all concrete insight generator plugin classes and the canonical priority registry.
"""

from app.intelligence.insight.base_insight_generator import BaseInsightGenerator
from app.intelligence.insight.generators.anomaly_insights_generator import AnomalyInsightsGenerator
from app.intelligence.insight.generators.business_rule_insights_generator import BusinessRuleInsightsGenerator
from app.intelligence.insight.generators.correlation_insights_generator import CorrelationInsightsGenerator
from app.intelligence.insight.generators.executive_summary_generator import ExecutiveSummaryGenerator
from app.intelligence.insight.generators.kpi_insights_generator import KPIInsightsGenerator
from app.intelligence.insight.generators.opportunity_insights_generator import OpportunityInsightsGenerator
from app.intelligence.insight.generators.trend_insights_generator import TrendInsightsGenerator

INSIGHT_GENERATOR_REGISTRY: tuple[type[BaseInsightGenerator], ...] = (
    KPIInsightsGenerator,
    TrendInsightsGenerator,
    CorrelationInsightsGenerator,
    AnomalyInsightsGenerator,
    BusinessRuleInsightsGenerator,
    OpportunityInsightsGenerator,
    ExecutiveSummaryGenerator,
)

__all__ = [
    "BaseInsightGenerator",
    "KPIInsightsGenerator",
    "TrendInsightsGenerator",
    "CorrelationInsightsGenerator",
    "AnomalyInsightsGenerator",
    "BusinessRuleInsightsGenerator",
    "OpportunityInsightsGenerator",
    "ExecutiveSummaryGenerator",
    "INSIGHT_GENERATOR_REGISTRY",
]
