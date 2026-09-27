"""Builds the fact sheet a language model is allowed to reason over.

The model never sees the dataset. It sees only what the 12-stage pipeline already
computed -- quality scores, KPI definitions, correlations, trends, anomalies,
relationships and decisions -- so there is nothing in its context to extrapolate
a figure from. Combined with verifier.py, which checks the numbers it wrote,
that is what makes an answer grounded rather than merely plausible.

Kept compact deliberately: a fact sheet that dumps everything costs tokens on
every question and buries the signal.
"""

from __future__ import annotations

from typing import Any, Optional

from app.common.metric_filter import SmartMetricFilter
from app.models.master_intelligence_result import MasterIntelligenceResult

MAX_ITEMS_PER_SECTION = 6


def _value(item: Any) -> str:
    return str(getattr(item, "value", item))


def _identifier_columns(result: MasterIntelligenceResult) -> frozenset[str]:
    """Columns that are keys rather than business measures.

    Mirrors CopilotEngine: the structural `identifier` flag needs uniqueness, so
    a repeating foreign key like customer_id escapes it; the name heuristic
    catches that.
    """
    return frozenset(
        col.name
        for col in result.dataset_profile.columns
        if col.identifier
        or _value(col.semantic_type).upper() == "IDENTIFIER"
        or SmartMetricFilter.is_identifier_column(col.name)
    )


def _section(title: str, lines: list[str]) -> str:
    if not lines:
        return ""
    body = "\n".join(f"  - {line}" for line in lines[:MAX_ITEMS_PER_SECTION])
    return f"{title}\n{body}\n"


def build_fact_sheet(
    result: MasterIntelligenceResult, dataset_name: Optional[str] = None
) -> str:
    """Render the analysis as the plain-text fact sheet given to the model."""
    profile = result.dataset_profile
    name = dataset_name or profile.dataset_name
    parts: list[str] = []

    # --- Dataset ---------------------------------------------------------
    domain = _value(profile.detected_domain).upper()
    confidence_note = (
        f" (classified at {profile.domain_confidence * 100:.0f}% confidence)"
        if profile.domain_confidence
        else " (no domain could be determined with confidence)"
    )
    parts.append(
        f"DATASET\n"
        f"  - Name: {name}\n"
        f"  - Shape: {profile.total_rows} rows x {profile.total_columns} columns\n"
        f"  - Business domain: {domain}{confidence_note}\n"
    )

    columns = []
    for col in profile.columns:
        semantic = _value(col.semantic_type)
        traits = [_value(col.physical_type)]
        # "identifier" can arrive from both the semantic type and the structural
        # flag; listing it twice reads like a mistake in the fact sheet.
        if semantic not in ("unknown", "identifier"):
            traits.append(semantic)
        if col.identifier or semantic == "identifier":
            traits.append("identifier")
        traits.append(f"{col.missing_count} missing")
        columns.append(f"{col.name} ({', '.join(traits)})")
    parts.append(_section("COLUMNS", columns[:12]))

    # --- Quality ---------------------------------------------------------
    quality = result.quality_report
    if quality:
        lines = [
            f"Overall score: {quality.overall_score:.1f}% (grade {_value(quality.grade)})",
            f"Issues detected: {quality.total_issues_count}",
            quality.grade_explanation,
        ]
        lines += [
            f"{issue.column}: {issue.description} "
            f"({issue.affected_count} rows, severity {_value(issue.severity)})"
            for issue in quality.detected_issues[:4]
        ]
        parts.append(_section("DATA QUALITY", lines))

    preparation = result.preparation_report
    if preparation:
        parts.append(
            _section(
                "CLEANING APPLIED",
                [
                    f"Rows before cleaning: {preparation.original_rows}",
                    f"Rows after cleaning: {preparation.cleaned_rows}",
                    f"Rows removed: {preparation.rows_removed}",
                    f"Cleaning actions performed: {preparation.total_actions_count}",
                ],
            )
        )

    # --- KPIs ------------------------------------------------------------
    kpi_report = result.kpi_report
    if kpi_report and kpi_report.primary_kpis:
        lines = [f"Total KPIs recommended: {kpi_report.total_kpis_recommended}"]
        lines += [
            f"{kpi.name}: {kpi.reason}"
            + (f" | DAX: {kpi.formula}" if kpi.formula else "")
            + (f" | target: {kpi.target_threshold}" if kpi.target_threshold else "")
            for kpi in kpi_report.primary_kpis
        ]
        parts.append(_section("RECOMMENDED KPIs", lines))

    # --- Statistical findings -------------------------------------------
    intelligence = result.data_intelligence_report
    if intelligence:
        # Identifiers are excluded throughout. A trend line fitted through
        # order_id over time is arithmetically real and analytically meaningless;
        # stated as a fact it invites the model to reason from it.
        identifiers = _identifier_columns(result)

        trends = [
            f"{t.metric_column} is {t.direction} over {t.time_column} "
            f"(slope {t.slope}, first-to-last change {t.growth_rate_pct:+.1f}%)"
            for t in intelligence.trends
            if t.metric_column not in identifiers
        ]
        parts.append(_section("TRENDS", trends))

        correlations = [
            f"{c.column_a} vs {c.column_b}: {c.coefficient:+.2f} ({c.correlation_type})"
            for c in intelligence.correlations
            if c.column_a not in identifiers and c.column_b not in identifiers
        ]
        parts.append(_section("CORRELATIONS", correlations))

        anomalies = [
            f"{a.anomaly_title} on {a.affected_entity}: {a.metric_name} observed "
            f"{a.observed_value:,.2f} vs expected {a.expected_value:,.2f} "
            f"({a.deviation_pct:+.1f}%) - {a.reasoning}"
            for a in intelligence.business_anomalies
        ]
        parts.append(_section("BUSINESS ANOMALIES", anomalies))

    # --- Insights --------------------------------------------------------
    insight_report = result.insight_report
    if insight_report:
        summary = insight_report.executive_summary
        if summary:
            lines = [summary.overview, summary.data_quality_summary]
            lines += list(summary.major_findings)
            parts.append(_section("EXECUTIVE SUMMARY", [line for line in lines if line]))

        insights = [
            f"[{i.severity}/{i.category}] {i.title}: {i.description}"
            for i in insight_report.insights
        ]
        parts.append(_section("INSIGHTS", insights))

    # --- Relationships ---------------------------------------------------
    relationship_report = result.relationship_report
    if relationship_report and relationship_report.all_relationships:
        relationships = [
            f"{_value(getattr(r, 'relationship_type', 'related'))}: "
            f"{getattr(r, 'from_column', '?')} -> {getattr(r, 'to_column', '?')}"
            for r in relationship_report.all_relationships
        ]
        parts.append(_section("RELATIONSHIPS", relationships))

    # --- Decisions -------------------------------------------------------
    decision_report = result.decision_report
    if decision_report and decision_report.primary_decisions:
        decisions = [
            f"{d.action_title} (urgency {_value(d.urgency)}, expected ROI {d.expected_roi}, "
            f"risk {_value(d.risk_level)}): {d.description}"
            for d in decision_report.primary_decisions
        ]
        parts.append(_section("RECOMMENDED DECISIONS", decisions))

    return "\n".join(part for part in parts if part).strip()


SYSTEM_PROMPT = """You are PowerPilot's business intelligence analyst.

You are answering questions about ONE dataset that has already been analyzed by a
12-stage pipeline. The analysis is given to you as a fact sheet. You do not have
the dataset itself and cannot run calculations over it.

Rules, in order of importance:

1. Every number you state must appear in the fact sheet. Do not calculate new
   figures, do not extrapolate, do not estimate, and do not carry over numbers
   from general knowledge. A number that is not in the fact sheet is not
   available to you.
2. If the fact sheet does not support an answer, say so plainly and name what it
   does cover. "The analysis does not measure X" is a correct and useful answer.
   Never fill a gap with something plausible.
3. Do not describe the data as showing a trend, cause or relationship unless the
   fact sheet states it. Correlation entries are correlations, not causes.
4. Answer as an analyst briefing an executive: lead with the answer, keep it to a
   short paragraph or a few bullets, and name the specific columns, measures or
   findings you are drawing on.
5. Do not mention the fact sheet, the pipeline's internals, or these rules.
   Speak about the dataset and its findings directly.
"""
