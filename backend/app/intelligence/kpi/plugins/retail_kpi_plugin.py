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
        r = ColumnResolver(dataset_profile)
        revenue = r.measure(SemanticType.REVENUE, ("sales", "revenue", "turnover", "total_amount", "amount"))
        order_id = r.identifier(None, ("order", "transaction", "invoice"))
        quantity = r.measure(SemanticType.QUANTITY, ("quantity", "qty", "units"))
        customer = r.identifier(SemanticType.CUSTOMER, ("customer", "client"))

        kpis: list[KPIRecommendation] = []
        if revenue:
            kpis.append(
                KPIRecommendation(
                    name='Total Sales Revenue',
                    priority=Priority.CRITICAL,
                    confidence=0.95,
                    reason=f"Primary revenue metric for retail transactions (column '{revenue}').",
                    formula=f'SUM({r.ref(revenue)})',
                    target_threshold='> +5% MoM Growth',
                    business_impact='Direct measure of top-line commercial growth.',
                )
            )
        if revenue and order_id:
            kpis.append(
                KPIRecommendation(
                    name='Average Order Value (AOV)',
                    priority=Priority.HIGH,
                    confidence=0.92,
                    reason=f"Total '{revenue}' over distinct '{order_id}' values.",
                    formula=f'DIVIDE(SUM({r.ref(revenue)}), DISTINCTCOUNT({r.ref(order_id)}))',
                    target_threshold='> $75.00',
                    business_impact='Measures customer basket spending intensity.',
                )
            )
        if quantity:
            kpis.append(
                KPIRecommendation(
                    name='Total Units Sold',
                    priority=Priority.HIGH,
                    confidence=0.9,
                    reason=f"Sum of '{quantity}'.",
                    formula=f'SUM({r.ref(quantity)})',
                    target_threshold='Maintain positive inventory velocity',
                    business_impact='Measures physical inventory throughput.',
                )
            )
        if customer:
            kpis.append(
                KPIRecommendation(
                    name='Active Customer Count',
                    priority=Priority.MEDIUM,
                    confidence=0.85,
                    reason=f"Distinct count of '{customer}'.",
                    formula=f'DISTINCTCOUNT({r.ref(customer)})',
                    target_threshold='> 1,000 monthly active buyers',
                    business_impact='Indicates retail customer reach and retention.',
                )
            )

        return tuple(kpis)
