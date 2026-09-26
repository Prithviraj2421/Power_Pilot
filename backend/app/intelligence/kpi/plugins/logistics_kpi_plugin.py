from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation
from app.models.relationship_models import RelationshipReport


class LogisticsKPIPlugin(BaseKPIPlugin):
    """
    KPI recommendation plugin for the LOGISTICS domain.
    """

    target_domain = DatasetDomain.LOGISTICS

    def recommend(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        entities: Optional[list[DetectedEntity]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[KPIRecommendation, ...]:
        tbl = dataset_profile.dataset_name

        kpis = [
            KPIRecommendation(
                name="Total Freight Expenditure",
                priority=Priority.CRITICAL,
                confidence=0.94,
                reason="Sum of shipment freight costs.",
                formula=f"SUM('{tbl}'[Freight_Cost])",
                target_threshold="Within logistics budget",
                business_impact="Primary measure of freight spend.",
            ),
            KPIRecommendation(
                name="Average Shipping Delay Days",
                priority=Priority.HIGH,
                confidence=0.90,
                reason="Average delay between scheduled and actual delivery date.",
                formula=f"AVERAGE('{tbl}'[Delay_Days])",
                target_threshold="< 1.0 Day",
                business_impact="Measures supply chain SLA compliance.",
            ),
            KPIRecommendation(
                name="Cost Per Shipped Unit",
                priority=Priority.HIGH,
                confidence=0.88,
                reason="Freight spend normalized per unit volume.",
                formula=f"SUM('{tbl}'[Freight_Cost]) / SUM('{tbl}'[Quantity_Shipped])",
                target_threshold="< $2.50 per unit",
                business_impact="Measures shipping cost efficiency.",
            ),
        ]

        return tuple(kpis)
