"""
Data Intelligence Engine facade for PowerPilot.

Analyzes raw DataFrame values alongside structural DatasetProfile, executive BusinessProfile,
and DetectedEntities to generate deep statistical, data quality, correlation, trend, outlier,
pattern, and business anomaly findings.
"""

from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain
from app.core.config import get_settings
from app.intelligence.stats.significance import apply_fdr, reportable
from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.intelligence.data.plugins import (
    BusinessAnomaliesPlugin,
    CorrelationPlugin,
    DataQualityPlugin,
    OutliersPlugin,
    PatternsPlugin,
    StatisticsPlugin,
    TrendsPlugin,
)
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import (
    BusinessAnomaly,
    CorrelationResult,
    DataIntelligenceReport,
    InsightCandidate,
    OutlierReport,
    PatternReport,
    QualityReport,
    StatisticalSummary,
    TrendResult,
)
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class DataIntelligenceEngine:
    """
    Facade orchestrating statistical, data quality, and domain-aware business analysis.

    Executes all registered Data Intelligence plugins, synthesizes findings into
    actionable InsightCandidates, and returns a unified DataIntelligenceReport.
    """

    def __init__(self) -> None:
        """Initialize all individual data intelligence plugins."""
        self._quality_plugin = DataQualityPlugin()
        self._statistics_plugin = StatisticsPlugin()
        self._correlation_plugin = CorrelationPlugin()
        self._trends_plugin = TrendsPlugin()
        self._outliers_plugin = OutliersPlugin()
        self._patterns_plugin = PatternsPlugin()
        self._anomalies_plugin = BusinessAnomaliesPlugin()

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> DataIntelligenceReport:
        """
        Perform complete data intelligence analysis across DataFrame values and metadata.

        Parameters
        ----------
        df : pd.DataFrame
            The raw dataset DataFrame.
        dataset_profile : DatasetProfile
            The structural profile from Schema Analyzer.
        business_profile : Optional[BusinessProfile]
            The executive profile from Business Profiler.
        entities : Optional[list[DetectedEntity]]
            Optional list of detected semantic entities.

        Returns
        -------
        DataIntelligenceReport
            Unified, explainable intelligence report.
        """
        entities_list = entities or []

        # 1. Quality Report
        quality_rep = self._run_plugin(
            self._quality_plugin, df, dataset_profile, business_profile, entities_list
        )
        if not isinstance(quality_rep, QualityReport):
            quality_rep = QualityReport(
                overall_score=100.0,
                completeness_score=100.0,
                uniqueness_score=100.0,
                validity_score=100.0,
                total_issues=0,
            )

        # 2. Statistical Summary
        stats_sum = self._run_plugin(
            self._statistics_plugin, df, dataset_profile, business_profile, entities_list
        )
        if not isinstance(stats_sum, StatisticalSummary):
            stats_sum = StatisticalSummary(
                total_rows=len(df),
                numeric_columns_count=0,
                categorical_columns_count=0,
                date_columns_count=0,
            )

        # 3 + 4. Correlations and trends. Every pair and every metric-over-time tested goes into ONE family and is
        # corrected for the number of tests together; only findings that survive and are big enough become insights.
        tested_correlations = self._run_tests(self._correlation_plugin, df, dataset_profile, business_profile, entities_list)
        tested_trends = self._run_tests(self._trends_plugin, df, dataset_profile, business_profile, entities_list)
        correlations_tuple, trends_tuple, noise = self._correct_for_multiple_testing(tested_correlations, tested_trends)

        # 5. Outliers
        outliers = self._run_plugin(
            self._outliers_plugin, df, dataset_profile, business_profile, entities_list
        )
        outliers_tuple = tuple(outliers) if isinstance(outliers, (list, tuple)) else ()

        # 6. Patterns
        patterns = self._run_plugin(
            self._patterns_plugin, df, dataset_profile, business_profile, entities_list
        )
        patterns_tuple = tuple(patterns) if isinstance(patterns, (list, tuple)) else ()

        # 7. Business Anomalies
        anomalies = self._run_plugin(
            self._anomalies_plugin, df, dataset_profile, business_profile, entities_list
        )
        anomalies_tuple = tuple(anomalies) if isinstance(anomalies, (list, tuple)) else ()

        # Synthesize Insight Candidates
        insights = self._synthesize_insights(
            quality_rep, correlations_tuple, trends_tuple, outliers_tuple, patterns_tuple, anomalies_tuple
        )

        domain = getattr(dataset_profile, "detected_domain", DatasetDomain.UNKNOWN)
        overall_health = self._calculate_overall_health(quality_rep, anomalies_tuple)

        return DataIntelligenceReport(
            quality_report=quality_rep,
            statistical_summary=stats_sum,
            correlations=correlations_tuple,
            trends=trends_tuple,
            outliers=outliers_tuple,
            patterns=patterns_tuple,
            business_anomalies=anomalies_tuple,
            insights=tuple(insights),
            domain=domain,
            overall_health_score=overall_health,
            tests_run=noise["tests_run"],
            rejected_as_noise=noise["rejected_as_noise"],
            below_effect_threshold=noise["below_effect_threshold"],
            fdr_q=noise["fdr_q"],
        )

    def _run_tests(self, plugin, df, dataset_profile, business_profile, entities) -> tuple:
        """Every relationship a plugin tested, uncorrected (an error in the plugin means none)."""
        try:
            return tuple(plugin.test_all(df, dataset_profile, business_profile, entities))
        except Exception:
            return ()

    @staticmethod
    def _correct_for_multiple_testing(correlations: tuple, trends: tuple) -> tuple[tuple, tuple, dict]:
        settings = get_settings()
        q, floor = settings.insight_fdr_q, settings.insight_min_effect_size
        corrected = apply_fdr([*correlations, *trends], q)
        corrected_correlations, corrected_trends = corrected[: len(correlations)], corrected[len(correlations) :]
        survivors = [f for f in corrected if f.survived_fdr]
        reportable_all = [f for f in survivors if reportable(f, floor)]
        keep = lambda items: tuple(sorted((f for f in items if reportable(f, floor)), key=lambda f: -(f.effect_size or 0)))  # noqa: E731
        return keep(corrected_correlations), keep(corrected_trends), {
            "tests_run": len(corrected),
            "rejected_as_noise": len(corrected) - len(survivors),
            "below_effect_threshold": len(survivors) - len(reportable_all),
            "fdr_q": q,
        }

    def _run_plugin(
        self,
        plugin: BaseDataIntelligencePlugin,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile],
        entities: list[DetectedEntity],
    ):
        """Run plugin safely with error boundary."""
        try:
            return plugin.analyze(df, dataset_profile, business_profile, entities)
        except Exception:
            return None

    def _synthesize_insights(
        self,
        quality: QualityReport,
        correlations: tuple[CorrelationResult, ...],
        trends: tuple[TrendResult, ...],
        outliers: tuple[OutlierReport, ...],
        patterns: tuple[PatternReport, ...],
        anomalies: tuple[BusinessAnomaly, ...],
    ) -> list[InsightCandidate]:
        """Synthesize actionable executive insights from raw plugin reports."""
        insights: list[InsightCandidate] = []

        # Quality Insights
        if quality.total_issues > 0:
            insights.append(
                InsightCandidate(
                    title="Data Quality Attention Required",
                    category="QUALITY",
                    impact="HIGH" if quality.overall_score < 70 else "MEDIUM",
                    description=f"Identified {quality.total_issues} data quality issues with overall score of {quality.overall_score:.1f}%.",
                    actionable_recommendation="Review missing values and data cleaning rules prior to downstream executive reporting.",
                    confidence=0.95,
                    reasoning="Data quality scores fell below perfect threshold.",
                    evidence=quality.evidence,
                )
            )

        # Correlation Insights
        for corr in correlations:
            if abs(corr.coefficient) >= 0.7:
                insights.append(
                    InsightCandidate(
                        title=f"Strong {corr.correlation_type.replace('_', ' ').title()} Correlation",
                        category="CORRELATION",
                        impact="MEDIUM",
                        description=f"Column '{corr.column_a}' and '{corr.column_b}' exhibit correlation coefficient of {corr.coefficient:.2f}.",
                        actionable_recommendation=f"Consider using '{corr.column_a}' as a predictive driver for '{corr.column_b}'.",
                        confidence=corr.confidence,
                        reasoning=corr.reasoning,
                        evidence=(f"Pearson correlation r={corr.coefficient:.4f}",),
                    )
                )

        # Trend Insights
        for tr in trends:
            if abs(tr.growth_rate_pct) >= 10.0:
                insights.append(
                    InsightCandidate(
                        title=f"{tr.metric_column.replace('_', ' ').title()} {tr.direction.capitalize()} Trend",
                        category="TREND",
                        impact="HIGH",
                        description=f"Metric '{tr.metric_column}' shows a {tr.growth_rate_pct:.1f}% {tr.direction} trend over time.",
                        actionable_recommendation="Factor temporal growth trajectory into quarterly forecasts.",
                        confidence=tr.confidence,
                        reasoning=tr.reasoning,
                        evidence=(f"Slope = {tr.slope:.4f}, Growth = {tr.growth_rate_pct:.2f}%",),
                    )
                )

        # Business Anomaly Insights
        for anom in anomalies:
            insights.append(
                InsightCandidate(
                    title=anom.anomaly_title,
                    category="ANOMALY",
                    impact=anom.severity,
                    description=f"{anom.metric_name} observed value of {anom.observed_value} deviates by {anom.deviation_pct:.1f}% from expected.",
                    actionable_recommendation=f"Investigate root cause of anomaly in entity '{anom.affected_entity}'.",
                    confidence=anom.confidence,
                    reasoning=anom.reasoning,
                    evidence=anom.evidence,
                )
            )

        return insights

    @staticmethod
    def _calculate_overall_health(quality: QualityReport, anomalies: tuple[BusinessAnomaly, ...]) -> float:
        """Compute dataset overall health score out of 100."""
        score = quality.overall_score
        penalty = len(anomalies) * 5.0
        return round(max(0.0, min(100.0, score - penalty)), 2)
