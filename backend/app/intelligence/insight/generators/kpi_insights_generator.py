from typing import Optional

import pandas as pd

from app.common.enums import Priority
from app.intelligence.insight.base_insight_generator import BaseInsightGenerator
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import Insight, Recommendation


class KPIInsightsGenerator(BaseInsightGenerator):
    """
    Generates actionable business insights from recommended primary & secondary KPIs.
    """

    def generate(
        self,
        dataset_profile: DatasetProfile,
        business_profile: BusinessProfile,
        intelligence_report: DataIntelligenceReport,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[Insight, ...]:
        insights = []

        for kpi in business_profile.primary_kpis:
            severity = "CRITICAL" if kpi.priority == Priority.CRITICAL else "HIGH"
            prio = kpi.priority

            rec = Recommendation(
                action=f"Track and benchmark metric '{kpi.name}' on executive dashboards.",
                target_area=f"Domain: {business_profile.domain.value}",
                expected_impact="Improved visibility into core operational performance drivers.",
                priority=prio,
            )

            ins = Insight(
                title=f"Core Metric Alignment: {kpi.name}",
                description=f"Primary KPI recommendation '{kpi.name}' identified with formula `{kpi.formula}`.",
                category="KPI",
                severity=severity,
                priority=prio,
                confidence=kpi.confidence,
                business_impact=f"High strategic value for monitoring {business_profile.domain.value} performance.",
                recommendation=rec,
                supporting_evidence=(
                    f"Formula: {kpi.formula}",
                    f"Reasoning: {kpi.reason}",
                    f"Priority: {kpi.priority.value}",
                ),
            )
            insights.append(ins)

        return tuple(insights)
