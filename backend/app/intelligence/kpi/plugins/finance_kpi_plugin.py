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
        tbl = dataset_profile.dataset_name

        kpis = [
            KPIRecommendation(
                name="Gross Operating Revenue",
                priority=Priority.CRITICAL,
                confidence=0.96,
                reason="Core financial revenue metric from ledger postings.",
                formula=f"SUM('{tbl}'[Gross_Revenue])",
                target_threshold="> Prior Year Quarter",
                business_impact="Measures overall financial enterprise revenue scale.",
            ),
            KPIRecommendation(
                name="Net EBITDA Profit",
                priority=Priority.CRITICAL,
                confidence=0.94,
                reason="Net earnings before interest, taxes, depreciation, and amortization.",
                formula=f"SUM('{tbl}'[Revenue]) - SUM('{tbl}'[Operating_Expenses])",
                target_threshold="> 20% Net Margin",
                business_impact="Primary measure of operational profitability.",
            ),
            KPIRecommendation(
                name="Operating Expense Ratio",
                priority=Priority.HIGH,
                confidence=0.88,
                reason="Proportion of revenue consumed by operating overhead.",
                formula=f"(SUM('{tbl}'[Operating_Expenses]) / SUM('{tbl}'[Revenue])) * 100",
                target_threshold="< 65.0%",
                business_impact="Controls corporate cost structure efficiency.",
            ),
        ]

        return tuple(kpis)
