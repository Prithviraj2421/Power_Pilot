from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority, SemanticType
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.candidate import KPICandidate
from app.intelligence.kpi.column_resolver import ColumnResolver
from app.intelligence.kpi.ir import Difference, Ratio, total
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import RelationshipReport


class FinanceKPIPlugin(BaseKPIPlugin):
    """
    KPI plugin for the FINANCE domain.

    Columns come from the dataset (detected entities, then column names). A KPI whose
    columns are absent is skipped, never guessed.
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
    ) -> tuple[KPICandidate, ...]:
        r = ColumnResolver(dataset_profile, entities)
        revenue = r.measure(SemanticType.REVENUE, ("revenue", "income", "turnover", "sales", "amount"))
        expenses = r.measure(SemanticType.COST, ("expense", "expenses", "opex", "cost", "cogs"))

        kpis: list[KPICandidate] = []
        if revenue:
            kpis.append(
                KPICandidate(
                    name='Gross Operating Revenue',
                    priority=Priority.CRITICAL,
                    confidence=0.96,
                    reason=f"Core financial revenue metric (column '{revenue}').",
                    expression=total(revenue),
                    business_impact='Measures overall financial enterprise revenue scale.',
                    example_target='> Prior Year Quarter',
                )
            )
        if revenue and expenses and revenue != expenses:
            kpis.append(
                KPICandidate(
                    name='Net EBITDA Profit',
                    priority=Priority.CRITICAL,
                    confidence=0.94,
                    reason=f"'{revenue}' less '{expenses}'.",
                    expression=Difference(total(revenue), total(expenses)),
                    business_impact='Primary measure of operational profitability.',
                    example_target='> 20% Net Margin',
                )
            )
        if revenue and expenses and revenue != expenses:
            kpis.append(
                KPICandidate(
                    name='Operating Expense Ratio',
                    priority=Priority.HIGH,
                    confidence=0.88,
                    reason=f"'{expenses}' as a share of '{revenue}'.",
                    expression=Ratio(total(expenses), total(revenue), scale=100),
                    business_impact='Controls corporate cost structure efficiency.',
                    example_target='< 65.0%',
                )
            )

        return tuple(kpis)
