from typing import Optional

import pandas as pd

from app.common.enums import Priority
from app.core.config import get_settings
from app.intelligence.stats.significance import reportable
from app.intelligence.insight.base_insight_generator import BaseInsightGenerator
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import Insight, Recommendation


class CorrelationInsightsGenerator(BaseInsightGenerator):
    """
    Generates actionable business insights from statistical column correlations.
    """

    def generate(
        self,
        dataset_profile: DatasetProfile,
        business_profile: BusinessProfile,
        intelligence_report: DataIntelligenceReport,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[Insight, ...]:
        insights = []
        floor = get_settings().insight_min_effect_size

        for corr in intelligence_report.correlations:
            if not reportable(corr, floor) or abs(corr.coefficient) < 0.5:
                continue  # not corrected-significant, or too weak to be a driver

            abs_r = abs(corr.coefficient)
            severity = "HIGH" if abs_r >= 0.8 else "MEDIUM"
            prio = Priority.HIGH if abs_r >= 0.75 else Priority.MEDIUM

            if corr.coefficient > 0:
                title = f"Strong Positive Driver: {corr.column_a} & {corr.column_b}"
                impact = f"Strong co-movement (r={corr.coefficient:.2f}) indicates increasing '{corr.column_a}' directly expands '{corr.column_b}'."
                action = f"Leverage '{corr.column_a}' as an executive driver variable to forecast '{corr.column_b}'."
            else:
                title = f"Inverse Trade-Off: {corr.column_a} vs {corr.column_b}"
                impact = f"Inverse relationship (r={corr.coefficient:.2f}) indicates an increase in '{corr.column_a}' reduces '{corr.column_b}'."
                action = f"Balance strategic trade-offs between '{corr.column_a}' and '{corr.column_b}'."

            rec = Recommendation(
                action=action,
                target_area=f"Correlation Pair: {corr.column_a} / {corr.column_b}",
                expected_impact="Enhanced predictive modeling and resource allocation precision.",
                priority=prio,
            )

            ins = Insight(
                title=title,
                description=corr.reasoning,
                category="CORRELATION",
                severity=severity,
                priority=prio,
                confidence=corr.confidence,
                business_impact=impact,
                recommendation=rec,
                supporting_evidence=(
                    f"Column A: {corr.column_a}",
                    f"Column B: {corr.column_b}",
                    f"Pearson r: {corr.coefficient:.4f}",
                    f"Correlation Type: {corr.correlation_type}",
                ),
            )
            insights.append(ins)

        return tuple(insights)
