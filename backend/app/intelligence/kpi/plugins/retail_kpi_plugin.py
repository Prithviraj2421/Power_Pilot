from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority, SemanticType
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.candidate import KPICandidate
from app.intelligence.kpi.column_resolver import ColumnResolver
from app.intelligence.kpi.ir import Ratio, distinct, total
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import RelationshipReport


class RetailKPIPlugin(BaseKPIPlugin):
    """
    KPI plugin for the RETAIL domain.

    Columns come from the dataset (detected entities, then column names). A KPI whose
    columns are absent is skipped, never guessed.
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
    ) -> tuple[KPICandidate, ...]:
        r = ColumnResolver(dataset_profile, entities)
        revenue = r.measure(SemanticType.REVENUE, ("sales", "revenue", "turnover", "total_amount", "amount"))
        order_id = r.identifier(None, ("order", "transaction", "invoice"))
        quantity = r.measure(SemanticType.QUANTITY, ("quantity", "qty", "units"))
        customer = r.identifier(SemanticType.CUSTOMER, ("customer", "client"))

        kpis: list[KPICandidate] = []
        if revenue:
            kpis.append(
                KPICandidate(
                    name='Total Sales Revenue',
                    priority=Priority.CRITICAL,
                    confidence=0.95,
                    reason=f"Primary revenue metric for retail transactions (column '{revenue}').",
                    expression=total(revenue),
                    business_impact='Direct measure of top-line commercial growth.',
                    example_target='> +5% MoM Growth',
                )
            )
        if revenue and order_id:
            kpis.append(
                KPICandidate(
                    name='Average Order Value (AOV)',
                    priority=Priority.HIGH,
                    confidence=0.92,
                    reason=f"Total '{revenue}' over distinct '{order_id}' values.",
                    expression=Ratio(total(revenue), distinct(order_id)),
                    business_impact='Measures customer basket spending intensity.',
                    example_target='> $75.00',
                )
            )
        if quantity:
            kpis.append(
                KPICandidate(
                    name='Total Units Sold',
                    priority=Priority.HIGH,
                    confidence=0.9,
                    reason=f"Sum of '{quantity}'.",
                    expression=total(quantity),
                    business_impact='Measures physical inventory throughput.',
                    example_target='Maintain positive inventory velocity',
                )
            )
        if customer:
            kpis.append(
                KPICandidate(
                    name='Active Customer Count',
                    priority=Priority.MEDIUM,
                    confidence=0.85,
                    reason=f"Distinct count of '{customer}'.",
                    expression=distinct(customer),
                    business_impact='Indicates retail customer reach and retention.',
                    example_target='> 1,000 monthly active buyers',
                )
            )

        return tuple(kpis)
