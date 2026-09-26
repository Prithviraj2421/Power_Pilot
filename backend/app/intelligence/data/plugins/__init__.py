"""
Data Intelligence plugin registry.

Exports all concrete data intelligence plugin classes and the canonical priority registry.
"""

from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.intelligence.data.plugins.business_anomalies_plugin import BusinessAnomaliesPlugin
from app.intelligence.data.plugins.correlation_plugin import CorrelationPlugin
from app.intelligence.data.plugins.outliers_plugin import OutliersPlugin
from app.intelligence.data.plugins.patterns_plugin import PatternsPlugin
from app.intelligence.data.plugins.quality_plugin import DataQualityPlugin
from app.intelligence.data.plugins.statistics_plugin import StatisticsPlugin
from app.intelligence.data.plugins.trends_plugin import TrendsPlugin

DATA_INTELLIGENCE_REGISTRY: tuple[type[BaseDataIntelligencePlugin], ...] = (
    DataQualityPlugin,
    StatisticsPlugin,
    CorrelationPlugin,
    TrendsPlugin,
    OutliersPlugin,
    PatternsPlugin,
    BusinessAnomaliesPlugin,
)

__all__ = [
    "BaseDataIntelligencePlugin",
    "DataQualityPlugin",
    "StatisticsPlugin",
    "CorrelationPlugin",
    "TrendsPlugin",
    "OutliersPlugin",
    "PatternsPlugin",
    "BusinessAnomaliesPlugin",
    "DATA_INTELLIGENCE_REGISTRY",
]
