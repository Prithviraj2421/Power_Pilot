from typing import Optional

import pandas as pd

from app.common.enums import Priority
from app.intelligence.insight.base_insight_generator import BaseInsightGenerator
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import Insight, Recommendation


class AnomalyInsightsGenerator(BaseInsightGenerator):
    """
    Generates risk mitigation business insights from business anomalies and IQR outliers.
    """

    def generate(
        self,
        dataset_profile: DatasetProfile,
        business_profile: BusinessProfile,
        intelligence_report: DataIntelligenceReport,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[Insight, ...]:
        insights = []

        # 1. Business Anomalies
        for anom in intelligence_report.business_anomalies:
            severity = anom.severity
            prio = Priority.CRITICAL if severity == "CRITICAL" else (Priority.HIGH if severity == "HIGH" else Priority.MEDIUM)

            rec = Recommendation(
                action=f"Investigate anomaly in entity '{anom.affected_entity}' for metric '{anom.metric_name}'.",
                target_area=f"Entity: {anom.affected_entity}",
                expected_impact="Risk mitigation and data integrity enforcement.",
                priority=prio,
            )

            ins = Insight(
                title=f"Business Anomaly: {anom.anomaly_title}",
                description=anom.reasoning,
                category="ANOMALY",
                severity=severity,
                priority=prio,
                confidence=anom.confidence,
                business_impact=f"Observed value of {anom.observed_value} deviates by {anom.deviation_pct:.1f}% from expected.",
                recommendation=rec,
                supporting_evidence=anom.evidence,
            )
            insights.append(ins)

        # 2. Outliers
        for out in intelligence_report.outliers:
            if out.outlier_count == 0:
                continue

            severity = "HIGH" if out.outlier_percentage >= 5.0 else "MEDIUM"
            prio = Priority.HIGH if out.outlier_percentage >= 5.0 else Priority.MEDIUM

            rec = Recommendation(
                action=f"Filter or inspect {out.outlier_count} extreme outlier values in column '{out.column_name}'.",
                target_area=f"Column: {out.column_name}",
                expected_impact="Improved statistical stability and reporting reliability.",
                priority=prio,
            )

            ins = Insight(
                title=f"Extreme Outlier Cluster in '{out.column_name}'",
                description=out.reasoning,
                category="ANOMALY",
                severity=severity,
                priority=prio,
                confidence=out.confidence,
                business_impact=f"{out.outlier_percentage:.1f}% of values fall outside normal IQR bounds.",
                recommendation=rec,
                supporting_evidence=(
                    f"Outlier Count: {out.outlier_count}",
                    f"Outlier Percentage: {out.outlier_percentage:.2f}%",
                    f"Bounds: [{out.outlier_bounds[0]}, {out.outlier_bounds[1]}]",
                ),
            )
            insights.append(ins)

        return tuple(insights)
