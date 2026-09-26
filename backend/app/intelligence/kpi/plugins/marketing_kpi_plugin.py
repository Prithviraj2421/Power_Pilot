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


class MarketingKPIPlugin(BaseKPIPlugin):
    """
    KPI recommendation plugin for the MARKETING domain.
    """

    target_domain = DatasetDomain.MARKETING

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
                name="Return on Ad Spend (ROAS)",
                priority=Priority.CRITICAL,
                confidence=0.95,
                reason="Ratio of campaign revenue generated per dollar of ad spend.",
                formula=f"SUM('{tbl}'[Revenue]) / SUM('{tbl}'[Ad_Spend])",
                target_threshold="> 3.5x ROAS",
                business_impact="Measures ad spend efficiency.",
            ),
            KPIRecommendation(
                name="Cost Per Acquisition (CPA)",
                priority=Priority.HIGH,
                confidence=0.90,
                reason="Ad spend required per lead conversion.",
                formula=f"SUM('{tbl}'[Ad_Spend]) / SUM('{tbl}'[Conversions])",
                target_threshold="< $45.00",
                business_impact="Measures customer acquisition efficiency.",
            ),
            KPIRecommendation(
                name="Click-Through Rate (CTR %)",
                priority=Priority.MEDIUM,
                confidence=0.85,
                reason="Percentage of ad impressions converted to clicks.",
                formula=f"(SUM('{tbl}'[Clicks]) / SUM('{tbl}'[Impressions])) * 100",
                target_threshold="> 2.5%",
                business_impact="Measures ad creative engagement.",
            ),
        ]

        return tuple(kpis)
