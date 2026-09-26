"""Grounded conversational BI engine.

The Copilot answers strictly from a dataset's computed ``MasterIntelligenceResult``.
It has no generative model behind it, which is the point: it cannot hallucinate a
figure. The corollary is that when the analysis contains no evidence for a
question, the honest answer is to say so.

Earlier revisions of this module filled those gaps with hardcoded strings --
invented anomalies ("High variance detected in transaction volume"), invented
dimension names ("Region, Store_ID, Product_Category"), an invented KPI count --
which are indistinguishable from real findings to anyone reading the answer. All
of them are gone. Every string returned below is either derived from the dataset
or an explicit statement that the dataset does not support the question.
"""

import re
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from app.common.metric_filter import SmartMetricFilter
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.insight_models import Insight, InsightReport
from app.models.master_intelligence_result import MasterIntelligenceResult


@dataclass(slots=True, frozen=True)
class CopilotResponse:
    """
    Structured AI Copilot response payload.
    """

    answer: str
    intent: str
    evidence: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    suggested_followups: tuple[str, ...]


def _enum_value(value: Any) -> str:
    """Render a StrEnum member or a plain string uniformly."""
    return str(getattr(value, "value", value))


class CopilotEngine:
    """
    Master AI Copilot facade for conversational BI and grounded context synthesis.
    """

    DECLINE_KEYWORDS = ("why", "decrease", "drop", "decline", "fall", "reduce", "loss")
    BREAKDOWN_KEYWORDS = ("region", "area", "sales by", "country", "territory", "breakdown")
    ACTION_KEYWORDS = ("management", "action", "do", "recommend", "should", "strategy")
    KPI_KEYWORDS = ("kpi", "metric", "benchmark", "measure", "formula", "dax")
    QUALITY_KEYWORDS = ("quality", "missing", "clean", "duplicate", "grade", "null")

    @staticmethod
    def _matches(query: str, keywords: Sequence[str]) -> bool:
        """Whole-word keyword match.

        Substring matching is not good enough here: a bare ``"do"`` also matches
        inside "domain", "down" and "dollar", so "What is the domain?" would route
        to the management-actions handler. Word boundaries keep short keywords from
        hijacking unrelated questions, and still work for phrases like "sales by".

        The optional trailing ``s`` keeps plurals working -- "KPIs", "metrics",
        "measures" -- without letting a keyword match inside an unrelated word.
        """
        return any(re.search(rf"\b{re.escape(word)}s?\b", query) for word in keywords)

    def ask(self, query: str, result: MasterIntelligenceResult) -> CopilotResponse:
        """
        Process user query against grounded MasterIntelligenceResult context.
        """
        q_clean = query.lower().strip()

        if self._matches(q_clean, self.QUALITY_KEYWORDS):
            return self._handle_quality(result)
        if self._matches(q_clean, self.DECLINE_KEYWORDS):
            return self._handle_why_decrease(result)
        if self._matches(q_clean, self.BREAKDOWN_KEYWORDS):
            return self._handle_breakdown(result)
        if self._matches(q_clean, self.ACTION_KEYWORDS):
            return self._handle_management_actions(result)
        if self._matches(q_clean, self.KPI_KEYWORDS):
            return self._handle_kpis(result)
        return self._handle_general_qa(query, result)

    # -- shared helpers -----------------------------------------------------

    @staticmethod
    def _dataset_name(result: MasterIntelligenceResult) -> str:
        return result.dataset_profile.dataset_name

    @staticmethod
    def _domain(result: MasterIntelligenceResult) -> str:
        return _enum_value(result.dataset_profile.detected_domain).upper()

    @staticmethod
    def _decision_titles(result: MasterIntelligenceResult, limit: int = 3) -> tuple[str, ...]:
        """Action titles from the Decision Engine, or empty if it produced none."""
        if result.decision_report and result.decision_report.primary_decisions:
            return tuple(d.action_title for d in result.decision_report.primary_decisions[:limit])
        return ()

    @staticmethod
    def _insights_in_categories(
        report: Optional[InsightReport], categories: Sequence[str]
    ) -> tuple[Insight, ...]:
        """Insights whose category is one of ``categories``.

        Category matters for causal questions: the report's KPI insights are
        *recommendations* ("consider tracking Total Revenue"), not explanations,
        so citing them as causes of a decline produces a confident non-answer.
        """
        if report is None or not report.insights:
            return ()
        wanted = {c.upper() for c in categories}
        return tuple(i for i in report.insights if i.category.upper() in wanted)

    @staticmethod
    def _declining_trends(
        report: Optional[DataIntelligenceReport],
        exclude_columns: frozenset[str] = frozenset(),
    ) -> tuple[str, ...]:
        """Declining trends over real business measures, described in real numbers.

        Two things are deliberately filtered here:

        * ``exclude_columns`` drops identifier columns. A trend line fitted through
          ``customer_id`` over time is arithmetically valid and completely
          meaningless, and citing it as a cause of a decline is worse than silence.
        * ``growth_rate_pct`` is only reported when its sign agrees with the slope.
          The trends plugin derives ``direction`` from a regression slope over every
          point but ``growth_rate_pct`` from the first and last value alone, so the
          two can disagree -- which produced answers like "decreasing (+17.6%)".
          When they conflict, the slope wins and the endpoint figure is dropped.
        """
        if report is None or not report.trends:
            return ()

        declining = []
        for trend in report.trends:
            direction = trend.direction.lower()
            if not ("decreas" in direction or "declin" in direction or "down" in direction):
                continue
            if trend.metric_column in exclude_columns:
                continue

            description = f"{trend.metric_column} is {trend.direction} over {trend.time_column}"
            if trend.growth_rate_pct < 0:
                description += f" ({trend.growth_rate_pct:+.1f}% first to last)"
            declining.append(description)

        return tuple(declining)

    @staticmethod
    def _negative_correlations(
        report: Optional[DataIntelligenceReport],
        exclude_columns: frozenset[str] = frozenset(),
    ) -> tuple[str, ...]:
        """Negative correlations between real business measures, never identifiers."""
        if report is None or not report.correlations:
            return ()
        return tuple(
            f"{c.column_a} and {c.column_b} are negatively correlated ({c.coefficient:+.2f})"
            for c in report.correlations
            if c.coefficient < 0
            and "negative" in c.correlation_type.lower()
            and c.column_a not in exclude_columns
            and c.column_b not in exclude_columns
        )

    @staticmethod
    def _identifier_columns(result: MasterIntelligenceResult) -> frozenset[str]:
        """Columns that are keys rather than business measures.

        Two checks, because either alone leaks. The Schema Analyzer's ``identifier``
        flag requires actual uniqueness, so a repeating foreign key like
        ``customer_id`` (25 distinct values over 60 rows) is not caught by it. The
        name heuristic catches that, and the structural flag catches keys whose
        names give nothing away.
        """
        return frozenset(
            col.name
            for col in result.dataset_profile.columns
            if col.identifier
            or _enum_value(col.semantic_type).upper() == "IDENTIFIER"
            or SmartMetricFilter.is_identifier_column(col.name)
        )

    @staticmethod
    def _business_anomalies(report: Optional[DataIntelligenceReport]) -> tuple[str, ...]:
        """Domain anomalies, using BusinessAnomaly's real fields.

        Note: this previously read ``anomaly.description``, which does not exist on
        BusinessAnomaly -- so the Copilot raised AttributeError for any dataset
        that actually produced an anomaly.
        """
        if report is None or not report.business_anomalies:
            return ()
        return tuple(
            f"{a.anomaly_title} ({a.severity}) on {a.affected_entity}: {a.reasoning} "
            f"[{a.metric_name} observed {a.observed_value:,.2f} vs expected "
            f"{a.expected_value:,.2f}, {a.deviation_pct:+.1f}%]"
            for a in report.business_anomalies
        )

    def _available_topics(self, result: MasterIntelligenceResult) -> str:
        """What this dataset *can* answer, for use when a question has no support."""
        topics = []
        if result.quality_report:
            topics.append("data quality")
        if result.kpi_report and result.kpi_report.primary_kpis:
            topics.append("KPIs and DAX measures")
        if result.relationship_report and result.relationship_report.all_relationships:
            topics.append("entity relationships")
        if result.decision_report and result.decision_report.primary_decisions:
            topics.append("recommended actions")
        return ", ".join(topics) if topics else "the dataset profile"

    # -- intent handlers ----------------------------------------------------

    def _handle_why_decrease(self, result: MasterIntelligenceResult) -> CopilotResponse:
        """Explain a decline using only causal signals present in the analysis."""
        intelligence = result.data_intelligence_report

        # Only signals whose *direction* can be verified count as evidence of a
        # decline. Trend and correlation insights are free text, so their direction
        # cannot be checked -- citing them would let a +1.00 positive correlation
        # be presented as a cause of a decrease. The structured trends and
        # correlations below are filtered by sign instead, and ANOMALY insights are
        # deviations by definition.
        identifiers = self._identifier_columns(result)
        evidence = (
            self._business_anomalies(intelligence)
            + self._declining_trends(intelligence, exclude_columns=identifiers)
            + self._negative_correlations(intelligence, exclude_columns=identifiers)
            + tuple(
                i.description
                for i in self._insights_in_categories(result.insight_report, ("ANOMALY",))
                if i.severity.upper() in ("CRITICAL", "HIGH")
            )
        )

        if evidence:
            answer = (
                f"Across the {self._domain(result)} analysis of "
                f"'{self._dataset_name(result)}', {len(evidence)} contributing "
                f"signal(s) point to the decline. The strongest is: {evidence[0]}"
            )
        else:
            # No fabricated cause. The analysis genuinely found no decline signal.
            answer = (
                f"I found no declining trend, negative correlation or business anomaly in "
                f"'{self._dataset_name(result)}', so I cannot attribute a decrease from this "
                f"dataset. That may mean there is no decline in the data, or that the dataset "
                f"lacks the time span needed to detect one. I can speak to "
                f"{self._available_topics(result)} instead."
            )

        return CopilotResponse(
            answer=answer,
            intent="WHY_DECREASE",
            evidence=evidence[:5],
            recommended_actions=self._decision_titles(result),
            suggested_followups=(
                "What should management do next?",
                "How is the data quality?",
                "What are my key KPIs?",
            ),
        )

    def _handle_breakdown(self, result: MasterIntelligenceResult) -> CopilotResponse:
        """List the dimensions actually present in this dataset."""
        dimensions = [
            col.name
            for col in result.dataset_profile.columns
            if _enum_value(col.physical_type).upper() in ("CATEGORICAL", "TEXT")
        ]
        measures = [
            col.name
            for col in result.dataset_profile.columns
            if _enum_value(col.physical_type).upper() in ("INTEGER", "FLOAT", "DECIMAL")
            and not col.identifier
        ]

        if dimensions:
            answer = (
                f"'{self._dataset_name(result)}' can be broken down by "
                f"{len(dimensions)} dimension(s): {', '.join(dimensions[:6])}."
            )
            if measures:
                answer += f" Available measures include: {', '.join(measures[:4])}."
        else:
            answer = (
                f"'{self._dataset_name(result)}' has no categorical or text columns, so there "
                f"is nothing to break down by. Every column is numeric, a date, or an "
                f"identifier."
            )

        return CopilotResponse(
            answer=answer,
            intent="DIMENSIONAL_BREAKDOWN",
            evidence=tuple(f"Dimension: {d}" for d in dimensions[:6]),
            recommended_actions=(
                ("Filter the Executive Dashboard by one of these dimensions",)
                if dimensions
                else ()
            ),
            suggested_followups=(
                "What are my key KPIs?",
                "What should management do next?",
                "How is the data quality?",
            ),
        )

    def _handle_management_actions(self, result: MasterIntelligenceResult) -> CopilotResponse:
        """Report the Decision Engine's recommendations, or that it produced none."""
        decisions = (
            result.decision_report.primary_decisions if result.decision_report else ()
        )

        detailed = tuple(
            f"{d.action_title} (urgency: {_enum_value(d.urgency)}, expected ROI: {d.expected_roi})"
            for d in decisions
        )

        if detailed:
            answer = (
                f"The Decision Engine produced {len(detailed)} prioritized action(s) for "
                f"'{self._dataset_name(result)}'. Top priority: {detailed[0]}"
            )
        else:
            answer = (
                f"The Decision Engine produced no strategic actions for "
                f"'{self._dataset_name(result)}'. It needs recognizable business measures "
                f"(revenue, cost, profit, quantity) and enough rows to establish a baseline. "
                f"I can speak to {self._available_topics(result)} instead."
            )

        return CopilotResponse(
            answer=answer,
            intent="MANAGEMENT_ACTION",
            evidence=detailed[:3],
            recommended_actions=tuple(d.action_title for d in decisions),
            suggested_followups=(
                "Why did profit decrease?",
                "What are my key KPIs?",
                "How is the data quality?",
            ),
        )

    def _handle_kpis(self, result: MasterIntelligenceResult) -> CopilotResponse:
        """Report the recommended KPIs and their real DAX formulas."""
        kpi_report = result.kpi_report
        primary = kpi_report.primary_kpis if kpi_report else ()

        if primary:
            answer = (
                f"PowerPilot recommended {kpi_report.total_kpis_recommended} KPI(s) for "
                f"'{self._dataset_name(result)}', {len(primary)} of them primary: "
                f"{', '.join(k.name for k in primary[:4])}. "
                f"Each carries an executable DAX formula for Power BI Desktop."
            )
            evidence = tuple(
                f"{k.name}: {k.formula}" if k.formula else k.name for k in primary[:4]
            )
        else:
            answer = (
                f"No KPIs were recommended for '{self._dataset_name(result)}'. The KPI Engine "
                f"matches recognizable business entities (revenue, cost, profit, quantity, "
                f"customer) against domain templates, and this dataset did not provide them. "
                f"I can speak to {self._available_topics(result)} instead."
            )
            evidence = ()

        return CopilotResponse(
            answer=answer,
            intent="KPI_PERFORMANCE",
            evidence=evidence,
            recommended_actions=(
                (
                    "Copy the DAX measures into Power BI Desktop",
                    "Export the Tabular Model BIM schema",
                )
                if primary
                else ()
            ),
            suggested_followups=(
                "What should management do next?",
                "How is the data quality?",
                "Show me the dimensions I can break down by.",
            ),
        )

    def _handle_quality(self, result: MasterIntelligenceResult) -> CopilotResponse:
        """Report the Stage 1 quality assessment and what cleaning actually changed."""
        quality = result.quality_report
        preparation = result.preparation_report

        if quality is None:
            return CopilotResponse(
                answer=(
                    f"No quality assessment is available for '{self._dataset_name(result)}'."
                ),
                intent="DATA_QUALITY",
                evidence=(),
                recommended_actions=(),
                suggested_followups=("What are my key KPIs?", "What should management do next?"),
            )

        answer = (
            f"'{self._dataset_name(result)}' scored {quality.overall_score:.1f}% "
            f"(grade {_enum_value(quality.grade)}) with {quality.total_issues_count} issue(s) "
            f"detected. {quality.grade_explanation}"
        )

        evidence = tuple(
            f"{issue.column}: {issue.description} "
            f"({issue.affected_count} rows, {issue.severity})"
            for issue in quality.detected_issues[:4]
        )

        if preparation:
            answer += (
                f" Cleaning took {preparation.original_rows} rows to "
                f"{preparation.cleaned_rows} ({preparation.rows_removed} removed) across "
                f"{preparation.total_actions_count} action(s)."
            )

        return CopilotResponse(
            answer=answer,
            intent="DATA_QUALITY",
            evidence=evidence,
            recommended_actions=tuple(
                issue.recommended_treatment for issue in quality.detected_issues[:3]
            ),
            suggested_followups=(
                "What are my key KPIs?",
                "What should management do next?",
                "Show me the dimensions I can break down by.",
            ),
        )

    def _handle_general_qa(self, query: str, result: MasterIntelligenceResult) -> CopilotResponse:
        profile = result.dataset_profile
        summary = (
            result.business_profile.executive_summary
            if result.business_profile
            else f"{self._domain(result)} dataset analysis complete."
        )

        answer = (
            f"Summary for '{profile.dataset_name}': {summary} "
            f"The dataset holds {profile.total_rows} rows and {profile.total_columns} columns, "
            f"classified as {self._domain(result)} at "
            f"{profile.domain_confidence * 100:.0f}% confidence."
        )

        evidence: tuple[str, ...] = (
            f"Domain: {self._domain(result)}",
            f"Shape: {profile.total_rows} rows x {profile.total_columns} columns",
        )
        if result.quality_report:
            evidence += (
                f"Quality: grade {_enum_value(result.quality_report.grade)} "
                f"({result.quality_report.overall_score:.1f}%)",
            )

        return CopilotResponse(
            answer=answer,
            intent="GENERAL_QA",
            evidence=evidence,
            recommended_actions=self._decision_titles(result),
            suggested_followups=(
                "How is the data quality?",
                "What are my key KPIs?",
                "What should management do next?",
            ),
        )
