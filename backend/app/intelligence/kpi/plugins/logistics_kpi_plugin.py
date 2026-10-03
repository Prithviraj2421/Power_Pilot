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
        r = ColumnResolver(dataset_profile)
        freight = r.measure(SemanticType.COST, ("freight", "shipping_cost", "shipping", "cost"))
        delay = r.measure(None, ("delay", "late"))
        units = r.measure(SemanticType.QUANTITY, ("quantity", "qty", "units", "weight"))

        kpis: list[KPIRecommendation] = []
        if freight:
            kpis.append(
                KPIRecommendation(
                    name='Total Freight Expenditure',
                    priority=Priority.CRITICAL,
                    confidence=0.94,
                    reason=f"Sum of '{freight}'.",
                    formula=f'SUM({r.ref(freight)})',
                    target_threshold='Within logistics budget',
                    business_impact='Primary measure of freight spend.',
                )
            )
        if delay:
            kpis.append(
                KPIRecommendation(
                    name='Average Shipping Delay Days',
                    priority=Priority.HIGH,
                    confidence=0.9,
                    reason=f"Average of '{delay}'.",
                    formula=f'AVERAGE({r.ref(delay)})',
                    target_threshold='< 1.0 Day',
                    business_impact='Measures supply chain SLA compliance.',
                )
            )
        if freight and units and units != freight:
            kpis.append(
                KPIRecommendation(
                    name='Cost Per Shipped Unit',
                    priority=Priority.HIGH,
                    confidence=0.88,
                    reason=f"'{freight}' per unit of '{units}'.",
                    formula=f'DIVIDE(SUM({r.ref(freight)}), SUM({r.ref(units)}))',
                    target_threshold='< $2.50 per unit',
                    business_impact='Measures shipping cost efficiency.',
                )
            )

        return tuple(kpis)
