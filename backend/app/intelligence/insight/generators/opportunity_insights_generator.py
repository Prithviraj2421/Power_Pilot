from typing import Optional

import pandas as pd

from app.common.enums import Priority
from app.intelligence.insight.base_insight_generator import BaseInsightGenerator
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import Insight, Recommendation


class OpportunityInsightsGenerator(BaseInsightGenerator):
    """
    Identifies high-leverage growth, cost-saving, and optimization opportunities from patterns and trends.
    """

    def generate(
        self,
        dataset_profile: DatasetProfile,
        business_profile: BusinessProfile,
        intelligence_report: DataIntelligenceReport,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[Insight, ...]:
        insights = []

        # 1. Pareto 80/20 Opportunities
        for pat in intelligence_report.patterns:
            if pat.pattern_type == "Pareto Distribution":
                rec = Recommendation(
                    action=f"Focus strategic account management on the top 20% segments in '{', '.join(pat.affected_columns)}'.",
                    target_area=f"Columns: {', '.join(pat.affected_columns)}",
                    expected_impact="Maximum revenue stabilization with minimum operational overhead.",
                    priority=Priority.HIGH,
                )
                ins = Insight(
                    title=f"High-Leverage Pareto Concentration in {', '.join(pat.affected_columns)}",
                    description=pat.description,
                    category="OPPORTUNITY",
                    severity="MEDIUM",
                    priority=Priority.HIGH,
                    confidence=pat.confidence,
                    business_impact="80/20 concentration enables targeted high-margin optimization.",
                    recommendation=rec,
                    supporting_evidence=(pat.description, pat.reasoning),
                )
                insights.append(ins)

        # 2. General Quality Improvement Opportunity
        if intelligence_report.quality_report.overall_score < 90.0:
            rec = Recommendation(
                action="Execute automated data cleaning pipeline to impute null values and resolve duplicates.",
                target_area="Dataset Data Hygiene",
                expected_impact=f"Boost data health score from {intelligence_report.quality_report.overall_score:.1f}% to 100%.",
                priority=Priority.HIGH,
            )
            ins = Insight(
                title="Data Quality Enhancement Opportunity",
                description=f"Current dataset quality score is {intelligence_report.quality_report.overall_score:.1f}%.",
                category="OPPORTUNITY",
                severity="MEDIUM",
                priority=Priority.HIGH,
                confidence=0.95,
                business_impact="Higher quality inputs improve downstream predictive accuracy.",
                recommendation=rec,
                supporting_evidence=intelligence_report.quality_report.evidence,
            )
            insights.append(ins)

        return tuple(insights)
