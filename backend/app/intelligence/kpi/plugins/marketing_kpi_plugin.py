from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority, SemanticType
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.column_resolver import ColumnResolver
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
        r = ColumnResolver(dataset_profile)
        revenue = r.measure(SemanticType.REVENUE, ("revenue", "sales", "income", "amount"))
        spend = r.measure(SemanticType.COST, ("spend", "cost", "budget"))
        conversions = r.measure(None, ("conversions", "conversion", "leads", "acquisitions"))
        clicks = r.measure(None, ("clicks", "click"))
        impressions = r.measure(None, ("impressions", "impression", "views"))

        kpis: list[KPIRecommendation] = []
        if revenue and spend:
            kpis.append(
                KPIRecommendation(
                    name='Return on Ad Spend (ROAS)',
                    priority=Priority.CRITICAL,
                    confidence=0.95,
                    reason=f"'{revenue}' generated per unit of '{spend}'.",
                    formula=f'DIVIDE(SUM({r.ref(revenue)}), SUM({r.ref(spend)}))',
                    target_threshold='> 3.5x ROAS',
                    business_impact='Measures ad spend efficiency.',
                )
            )
        if spend and conversions:
            kpis.append(
                KPIRecommendation(
                    name='Cost Per Acquisition (CPA)',
                    priority=Priority.HIGH,
                    confidence=0.9,
                    reason=f"'{spend}' per '{conversions}'.",
                    formula=f'DIVIDE(SUM({r.ref(spend)}), SUM({r.ref(conversions)}))',
                    target_threshold='< $45.00',
                    business_impact='Measures customer acquisition efficiency.',
                )
            )
        if clicks and impressions:
            kpis.append(
                KPIRecommendation(
                    name='Click-Through Rate (CTR %)',
                    priority=Priority.MEDIUM,
                    confidence=0.85,
                    reason=f"'{clicks}' as a share of '{impressions}'.",
                    formula=f'DIVIDE(SUM({r.ref(clicks)}), SUM({r.ref(impressions)})) * 100',
                    target_threshold='> 2.5%',
                    business_impact='Measures ad creative engagement.',
                )
            )

        return tuple(kpis)
