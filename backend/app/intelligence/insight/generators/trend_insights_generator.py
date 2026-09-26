from typing import Optional

import pandas as pd

from app.common.enums import Priority
from app.intelligence.insight.base_insight_generator import BaseInsightGenerator
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import Insight, Recommendation


class TrendInsightsGenerator(BaseInsightGenerator):
    """
    Generates actionable business insights from time-series growth trends.
    """

    def generate(
        self,
        dataset_profile: DatasetProfile,
        business_profile: BusinessProfile,
        intelligence_report: DataIntelligenceReport,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[Insight, ...]:
        insights = []

        for trend in intelligence_report.trends:
            abs_growth = abs(trend.growth_rate_pct)
            severity = "HIGH" if abs_growth >= 25.0 else ("MEDIUM" if abs_growth >= 10.0 else "LOW")
            prio = Priority.HIGH if abs_growth >= 20.0 else Priority.MEDIUM

            if trend.direction == "increasing":
                title = f"Upward Growth Trajectory in {trend.metric_column.replace('_', ' ').title()}"
                impact = f"Metric increased by {trend.growth_rate_pct:.1f}% over the evaluated timeframe."
                action = f"Capitalize on positive trajectory by scaling operational support for '{trend.metric_column}'."
            elif trend.direction == "decreasing":
                title = f"Downward Trajectory Alert in {trend.metric_column.replace('_', ' ').title()}"
                impact = f"Metric contracted by {trend.growth_rate_pct:.1f}% over the evaluated timeframe."
                action = f"Conduct root-cause audit to arrest declining trend in '{trend.metric_column}'."
            else:
                title = f"Stable Performance in {trend.metric_column.replace('_', ' ').title()}"
                impact = "Metric maintained steady performance with negligible slope."
                action = f"Monitor '{trend.metric_column}' for potential growth inflection points."

            rec = Recommendation(
                action=action,
                target_area=f"Time Column: {trend.time_column}",
                expected_impact="Proactive performance optimization based on temporal signals.",
                priority=prio,
            )

            ins = Insight(
                title=title,
                description=trend.reasoning,
                category="TREND",
                severity=severity,
                priority=prio,
                confidence=trend.confidence,
                business_impact=impact,
                recommendation=rec,
                supporting_evidence=(
                    f"Time Column: {trend.time_column}",
                    f"Metric Column: {trend.metric_column}",
                    f"Slope: {trend.slope:.4f}",
                    f"Growth Rate: {trend.growth_rate_pct:.2f}%",
                ),
            )
            insights.append(ins)

        return tuple(insights)
