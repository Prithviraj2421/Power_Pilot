from typing import Optional

import pandas as pd

from app.intelligence.insight.base_insight_generator import BaseInsightGenerator
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import ExecutiveSummary


class ExecutiveSummaryGenerator(BaseInsightGenerator):
    """
    Synthesizes executive narrative describing dataset overview, quality, findings, risks, opportunities, and actions.
    """

    def generate(
        self,
        dataset_profile: DatasetProfile,
        business_profile: BusinessProfile,
        intelligence_report: DataIntelligenceReport,
        df: Optional[pd.DataFrame] = None,
    ) -> ExecutiveSummary:
        dataset_name = dataset_profile.dataset_name
        domain = business_profile.domain

        overview = (
            f"Dataset '{dataset_name}' comprises {dataset_profile.total_rows:,} records and {dataset_profile.total_columns} columns, "
            f"classified under the {domain.value} business domain (confidence: {business_profile.confidence:.2f}). "
            f"{business_profile.executive_summary}"
        )

        quality = intelligence_report.quality_report
        quality_summary = (
            f"Overall Data Quality Health Score: {intelligence_report.overall_health_score:.1f}% "
            f"(Completeness: {quality.completeness_score:.1f}%, Uniqueness: {quality.uniqueness_score:.1f}%, Validity: {quality.validity_score:.1f}%). "
            f"Identified {quality.total_issues} data hygiene issues requiring attention."
        )

        # Major Findings
        major_findings = []
        if business_profile.primary_kpis:
            major_findings.append(f"Recommended {len(business_profile.primary_kpis)} primary KPIs, led by '{business_profile.primary_kpis[0].name}'.")
        if intelligence_report.correlations:
            top_corr = intelligence_report.correlations[0]
            major_findings.append(f"Identified strong correlation (r={top_corr.coefficient:.2f}) between '{top_corr.column_a}' and '{top_corr.column_b}'.")
        if intelligence_report.trends:
            top_trend = intelligence_report.trends[0]
            major_findings.append(f"Detected {top_trend.direction} trend ({top_trend.growth_rate_pct:.1f}% growth) in metric '{top_trend.metric_column}'.")
        if not major_findings:
            major_findings.append("Structured profiling completed successfully with standard column distribution statistics.")

        # Top Risks
        top_risks = []
        for anom in intelligence_report.business_anomalies:
            top_risks.append(f"Business Anomaly: {anom.anomaly_title} in '{anom.affected_entity}'.")
        for out in intelligence_report.outliers:
            if out.outlier_percentage >= 5.0:
                top_risks.append(f"Extreme Outliers: {out.outlier_percentage:.1f}% of records in '{out.column_name}' exceed IQR bounds.")
        if not top_risks:
            top_risks.append("No critical domain anomalies or extreme outlier clusters detected.")

        # Key Opportunities
        key_opportunities = []
        for pat in intelligence_report.patterns:
            if pat.pattern_type == "Pareto Distribution":
                key_opportunities.append(f"80/20 Concentration: {pat.description}")
        if quality.overall_score < 90.0:
            key_opportunities.append("Automated Data Hygiene: Resolve null cells and duplicate rows to boost data health.")
        if not key_opportunities:
            key_opportunities.append(f"Explore predictive analytics using '{business_profile.measures[0]}' across key dimensions." if business_profile.measures else "Dataset is structured for standard reporting.")

        # Recommended Actions
        recommended_actions = (
            f"1. Deploy executive dashboard tracking primary KPIs: {', '.join(kpi.name for kpi in business_profile.primary_kpis[:3])}.",
            "2. Investigate flagged business anomalies and data quality issues prior to reporting.",
            "3. Leverage identified driver variables in FP&A and operational forecasting.",
        )

        return ExecutiveSummary(
            dataset_name=dataset_name,
            domain=domain,
            overview=overview,
            data_quality_summary=quality_summary,
            major_findings=tuple(major_findings),
            top_risks=tuple(top_risks),
            key_opportunities=tuple(key_opportunities),
            recommended_actions=recommended_actions,
        )
