from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority, SemanticType
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.candidate import KPICandidate
from app.intelligence.kpi.column_resolver import ColumnResolver
from app.intelligence.kpi.ir import Ratio, total
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import RelationshipReport


class MarketingKPIPlugin(BaseKPIPlugin):
    """
    KPI plugin for the MARKETING domain.

    Columns come from the dataset (detected entities, then column names). A KPI whose
    columns are absent is skipped, never guessed.
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
    ) -> tuple[KPICandidate, ...]:
        r = ColumnResolver(dataset_profile, entities)
        revenue = r.measure(SemanticType.REVENUE, ("revenue", "sales", "income", "amount"))
        spend = r.measure(SemanticType.COST, ("spend", "cost", "budget"))
        conversions = r.measure(None, ("conversions", "conversion", "leads", "acquisitions"))
        clicks = r.measure(None, ("clicks", "click"))
        impressions = r.measure(None, ("impressions", "impression", "views"))

        kpis: list[KPICandidate] = []
        if revenue and spend and revenue != spend:
            kpis.append(
                KPICandidate(
                    name='Return on Ad Spend (ROAS)',
                    priority=Priority.CRITICAL,
                    confidence=0.95,
                    reason=f"'{revenue}' generated per unit of '{spend}'.",
                    expression=Ratio(total(revenue), total(spend)),
                    business_impact='Measures ad spend efficiency.',
                    example_target='> 3.5x ROAS',
                )
            )
        if spend and conversions:
            kpis.append(
                KPICandidate(
                    name='Cost Per Acquisition (CPA)',
                    priority=Priority.HIGH,
                    confidence=0.9,
                    reason=f"'{spend}' per '{conversions}'.",
                    expression=Ratio(total(spend), total(conversions)),
                    business_impact='Measures customer acquisition efficiency.',
                    example_target='< $45.00',
                )
            )
        if clicks and impressions:
            kpis.append(
                KPICandidate(
                    name='Click-Through Rate (CTR %)',
                    priority=Priority.MEDIUM,
                    confidence=0.85,
                    reason=f"'{clicks}' as a share of '{impressions}'.",
                    expression=Ratio(total(clicks), total(impressions), scale=100),
                    business_impact='Measures ad creative engagement.',
                    example_target='> 2.5%',
                )
            )

        return tuple(kpis)
