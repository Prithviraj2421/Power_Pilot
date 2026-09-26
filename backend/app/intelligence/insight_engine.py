from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority
from app.intelligence.insight.base_insight_generator import BaseInsightGenerator
from app.intelligence.insight.generators import (
    AnomalyInsightsGenerator,
    BusinessRuleInsightsGenerator,
    CorrelationInsightsGenerator,
    ExecutiveSummaryGenerator,
    KPIInsightsGenerator,
    OpportunityInsightsGenerator,
    TrendInsightsGenerator,
)
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import ExecutiveSummary, Insight, InsightReport


class InsightEngine:
    """
    Facade orchestrating business insight generation and executive narrative synthesis.

    Runs all registered Insight Generator plugins, prioritizes insights, and produces a complete InsightReport.
    """

    def __init__(self) -> None:
        """Initialize all individual insight generator plugins."""
        self._kpi_gen = KPIInsightsGenerator()
        self._trend_gen = TrendInsightsGenerator()
        self._correlation_gen = CorrelationInsightsGenerator()
        self._anomaly_gen = AnomalyInsightsGenerator()
        self._business_rule_gen = BusinessRuleInsightsGenerator()
        self._opportunity_gen = OpportunityInsightsGenerator()
        self._exec_summary_gen = ExecutiveSummaryGenerator()

    def generate(
        self,
        dataset_profile: DatasetProfile,
        business_profile: BusinessProfile,
        intelligence_report: DataIntelligenceReport,
        df: Optional[pd.DataFrame] = None,
    ) -> InsightReport:
        """
        Synthesize technical findings and business intelligence into a prioritized InsightReport.

        Parameters
        ----------
        dataset_profile : DatasetProfile
            The structural dataset profile.
        business_profile : BusinessProfile
            The executive business profile.
        intelligence_report : DataIntelligenceReport
            The data intelligence report.
        df : Optional[pd.DataFrame]
            Optional raw dataset DataFrame.

        Returns
        -------
        InsightReport
            Unified, explainable insight report containing executive summary and prioritized insights.
        """
        kpi_insights = self._run_generator(self._kpi_gen, dataset_profile, business_profile, intelligence_report, df)
        trend_insights = self._run_generator(self._trend_gen, dataset_profile, business_profile, intelligence_report, df)
        corr_insights = self._run_generator(self._correlation_gen, dataset_profile, business_profile, intelligence_report, df)
        anomaly_insights = self._run_generator(self._anomaly_gen, dataset_profile, business_profile, intelligence_report, df)
        brule_insights = self._run_generator(self._business_rule_gen, dataset_profile, business_profile, intelligence_report, df)
        opp_insights = self._run_generator(self._opportunity_gen, dataset_profile, business_profile, intelligence_report, df)

        exec_summary = self._exec_summary_gen.generate(dataset_profile, business_profile, intelligence_report, df)
        if not isinstance(exec_summary, ExecutiveSummary):
            exec_summary = ExecutiveSummary(
                dataset_name=dataset_profile.dataset_name,
                domain=business_profile.domain,
                overview="Executive summary fallback.",
                data_quality_summary=f"Quality score: {intelligence_report.overall_health_score:.1f}%.",
            )

        all_insights_list: list[Insight] = []
        for group in (kpi_insights, trend_insights, corr_insights, anomaly_insights, brule_insights, opp_insights):
            if isinstance(group, (list, tuple)):
                for item in group:
                    if isinstance(item, Insight):
                        all_insights_list.append(item)

        # Sort insights by priority (CRITICAL > HIGH > MEDIUM > LOW) and confidence descending
        prio_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
        all_insights_list.sort(key=lambda x: (prio_order.get(x.priority, 2), -x.confidence))

        domain = business_profile.domain

        return InsightReport(
            executive_summary=exec_summary,
            insights=tuple(all_insights_list),
            kpi_insights=tuple(kpi_insights) if isinstance(kpi_insights, tuple) else (),
            trend_insights=tuple(trend_insights) if isinstance(trend_insights, tuple) else (),
            correlation_insights=tuple(corr_insights) if isinstance(corr_insights, tuple) else (),
            anomaly_insights=tuple(anomaly_insights) if isinstance(anomaly_insights, tuple) else (),
            business_rule_insights=tuple(brule_insights) if isinstance(brule_insights, tuple) else (),
            opportunity_insights=tuple(opp_insights) if isinstance(opp_insights, tuple) else (),
            domain=domain,
        )

    def _run_generator(
        self,
        generator: BaseInsightGenerator,
        dataset_profile: DatasetProfile,
        business_profile: BusinessProfile,
        intelligence_report: DataIntelligenceReport,
        df: Optional[pd.DataFrame],
    ):
        """Safely execute generator with exception boundary."""
        try:
            return generator.generate(dataset_profile, business_profile, intelligence_report, df)
        except Exception:
            return ()
