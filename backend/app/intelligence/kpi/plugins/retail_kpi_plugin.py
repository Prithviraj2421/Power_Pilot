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


class RetailKPIPlugin(BaseKPIPlugin):
    """
    KPI recommendation plugin for the RETAIL domain.
    """

    target_domain = DatasetDomain.RETAIL

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
                name="Total Sales Revenue",
                priority=Priority.CRITICAL,
                confidence=0.95,
                reason="Primary revenue metric for retail transactions.",
                formula=f"SUM('{tbl}'[Sales_Amount])",
                target_threshold="> +5% MoM Growth",
                business_impact="Direct measure of top-line commercial growth.",
            ),
            KPIRecommendation(
                name="Average Order Value (AOV)",
                priority=Priority.HIGH,
                confidence=0.92,
                reason="Calculated ratio of total revenue over total unique transaction orders.",
                formula=f"SUM('{tbl}'[Sales_Amount]) / DISTINCTCOUNT('{tbl}'[Order_ID])",
                target_threshold="> $75.00",
                business_impact="Measures customer basket spending intensity.",
            ),
            KPIRecommendation(
                name="Total Units Sold",
                priority=Priority.HIGH,
                confidence=0.90,
                reason="Sum of physical merchandise items moved.",
                formula=f"SUM('{tbl}'[Quantity])",
                target_threshold="Maintain positive inventory velocity",
                business_impact="Measures physical inventory throughput.",
            ),
            KPIRecommendation(
                name="Active Customer Count",
                priority=Priority.MEDIUM,
                confidence=0.85,
                reason="Distinct count of unique customer identifiers in period.",
                formula=f"DISTINCTCOUNT('{tbl}'[Customer_ID])",
                target_threshold="> 1,000 monthly active buyers",
                business_impact="Indicates retail customer reach and retention.",
            ),
        ]

        return tuple(kpis)
