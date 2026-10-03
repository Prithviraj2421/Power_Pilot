from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority, SemanticType
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.candidate import KPICandidate
from app.intelligence.kpi.column_resolver import ColumnResolver
from app.intelligence.kpi.ir import Ratio, average, total
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import RelationshipReport


class LogisticsKPIPlugin(BaseKPIPlugin):
    """
    KPI plugin for the LOGISTICS domain.

    Columns come from the dataset (detected entities, then column names). A KPI whose
    columns are absent is skipped, never guessed.
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
    ) -> tuple[KPICandidate, ...]:
        r = ColumnResolver(dataset_profile, entities)
        freight = r.measure(SemanticType.COST, ("freight", "shipping_cost", "shipping", "cost"))
        delay = r.measure(None, ("delay", "late"))
        units = r.measure(SemanticType.QUANTITY, ("quantity", "qty", "units", "weight"))

        kpis: list[KPICandidate] = []
        if freight:
            kpis.append(
                KPICandidate(
                    name='Total Freight Expenditure',
                    priority=Priority.CRITICAL,
                    confidence=0.94,
                    reason=f"Sum of '{freight}'.",
                    expression=total(freight),
                    business_impact='Primary measure of freight spend.',
                    example_target='Within logistics budget',
                )
            )
        if delay:
            kpis.append(
                KPICandidate(
                    name='Average Shipping Delay Days',
                    priority=Priority.HIGH,
                    confidence=0.9,
                    reason=f"Average of '{delay}'.",
                    expression=average(delay),
                    business_impact='Measures supply chain SLA compliance.',
                    example_target='< 1.0 Day',
                )
            )
        if freight and units and units != freight:
            kpis.append(
                KPICandidate(
                    name='Cost Per Shipped Unit',
                    priority=Priority.HIGH,
                    confidence=0.88,
                    reason=f"'{freight}' per unit of '{units}'.",
                    expression=Ratio(total(freight), total(units)),
                    business_impact='Measures shipping cost efficiency.',
                    example_target='< $2.50 per unit',
                )
            )

        return tuple(kpis)
