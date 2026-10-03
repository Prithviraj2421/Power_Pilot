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


class FinanceKPIPlugin(BaseKPIPlugin):
    """
    KPI recommendation plugin for the FINANCE domain.
    """

    target_domain = DatasetDomain.FINANCE

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
        revenue = r.measure(SemanticType.REVENUE, ("revenue", "income", "turnover", "sales", "amount"))
        expenses = r.measure(SemanticType.COST, ("expense", "expenses", "opex", "cost", "cogs"))

        kpis: list[KPIRecommendation] = []
        if revenue:
            kpis.append(
                KPIRecommendation(
                    name='Gross Operating Revenue',
                    priority=Priority.CRITICAL,
                    confidence=0.96,
                    reason=f"Core financial revenue metric (column '{revenue}').",
                    formula=f'SUM({r.ref(revenue)})',
                    target_threshold='> Prior Year Quarter',
                    business_impact='Measures overall financial enterprise revenue scale.',
                )
            )
        if revenue and expenses:
            kpis.append(
                KPIRecommendation(
                    name='Net EBITDA Profit',
                    priority=Priority.CRITICAL,
                    confidence=0.94,
                    reason=f"'{revenue}' less '{expenses}'.",
                    formula=f'SUM({r.ref(revenue)}) - SUM({r.ref(expenses)})',
                    target_threshold='> 20% Net Margin',
                    business_impact='Primary measure of operational profitability.',
                )
            )
        if revenue and expenses:
            kpis.append(
                KPIRecommendation(
                    name='Operating Expense Ratio',
                    priority=Priority.HIGH,
                    confidence=0.88,
                    reason=f"'{expenses}' as a share of '{revenue}'.",
                    formula=f'DIVIDE(SUM({r.ref(expenses)}), SUM({r.ref(revenue)})) * 100',
                    target_threshold='< 65.0%',
                    business_impact='Controls corporate cost structure efficiency.',
                )
            )

        return tuple(kpis)
