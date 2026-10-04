"""Builds the fact sheet a language model is allowed to reason over.

The model never sees the dataset. It sees only what the 12-stage pipeline already
computed -- quality scores, KPI values, correlations, trends, anomalies,
relationships and decisions -- so there is nothing in its context to extrapolate
a figure from.

Every number in the sheet carries a fact id and a meaning: ``2297200.86 [F12]``, with
``F12`` defined as "Total Sales Revenue (KPI value)", unit currency. The model must
cite the id beside each number it writes, and verifier.py checks the number against
*that* fact's value, unit and meaning. "Revenue is 9,994" cannot pass by finding 9,994
somewhere else in the sheet (the row count, say) any more.

Numbers inside the pipeline's own free-text findings (an insight's description, a quality
explanation) are tagged too, with the finding they came from as their meaning.

Kept compact deliberately: a fact sheet that dumps everything costs tokens on
every question and buries the signal.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from app.common.metric_filter import SmartMetricFilter
from app.intelligence.llm.facts import Fact, FactSheet, Unit, find_numbers, is_trivial
from app.models.master_intelligence_result import MasterIntelligenceResult

MAX_ITEMS_PER_SECTION = 6

_MONEY = re.compile(r"revenue|sales|profit|cost|expense|spend|price|amount|salary|budget|income|value of", re.IGNORECASE)
_RATE = re.compile(r"rate|margin|ratio|share|percent|%|churn|attrition|growth", re.IGNORECASE)


def _value(item: Any) -> str:
    return str(getattr(item, "value", item))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


class _Facts:
    """Hands out fact ids and remembers what each one means."""

    def __init__(self) -> None:
        self.facts: dict[str, Fact] = {}

    def add(self, key: str, value: float, unit: Unit, label: str) -> str:
        fact_id = f"F{len(self.facts) + 1}"
        self.facts[fact_id] = Fact(fact_id, key, float(value), unit, label)
        return fact_id

    def ref(self, text: str, key: str, value: float, unit: Unit, label: str) -> str:
        """``text`` followed by the id of a new fact holding ``value``."""
        return f"{text} [{self.add(key, value, unit, label)}]"

    def tag(self, text: str, key: str, label: str) -> str:
        """Tag every number in a free-text finding with a fact whose meaning is that finding."""
        out, last = [], 0
        for index, mention in enumerate(find_numbers(text)):
            if is_trivial(mention):
                continue
            unit: Unit = "percent" if mention.unit == "percent" else "currency" if mention.unit == "currency" else "number"
            fact_id = self.add(f"{key}.{index}", mention.value, unit, label)
            out.append(text[last : mention.end])
            out.append(f" [{fact_id}]")
            last = mention.end
        out.append(text[last:])
        return "".join(out)


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
    body = "\n".join(f"  - {line}" for line in lines)
    return f"{title}\n{body}\n"


def _kpi_unit(name: str, formula: Optional[str]) -> Unit:
    if _RATE.search(name):
        return "percent" if formula and re.search(r"\*\s*100\b", formula) else "ratio"
    return "currency" if _MONEY.search(name) else "number"


def build_facts(result: MasterIntelligenceResult, dataset_name: Optional[str] = None) -> FactSheet:
    """The analysis as a fact sheet: readable text, and the structured fact behind every id in it."""
    f = _Facts()
    profile = result.dataset_profile
    name = dataset_name or profile.dataset_name
    parts: list[str] = []

    # --- Dataset ---------------------------------------------------------
    domain = _value(profile.detected_domain).upper()
    if profile.domain_confidence:
        confidence = f.ref(f"{profile.domain_confidence * 100:.0f}%", "dataset.domain_confidence", profile.domain_confidence * 100,
                           "percent", "Confidence of the business-domain classification")
        confidence_note = f" (classified at {confidence} confidence)"
    else:
        confidence_note = " (no domain could be determined with confidence)"
    rows = f.ref(str(profile.total_rows), "dataset.rows", profile.total_rows, "count", "Number of rows in the dataset")
    cols = f.ref(str(profile.total_columns), "dataset.columns", profile.total_columns, "count", "Number of columns in the dataset")
    parts.append(
        f"DATASET\n"
        f"  - Name: {name}\n"
        f"  - Shape: {rows} rows x {cols} columns\n"
        f"  - Business domain: {domain}{confidence_note}\n"
    )

    columns = []
    for col in profile.columns[:12]:
        semantic = _value(col.semantic_type)
        traits = [_value(col.physical_type)]
        # "identifier" can arrive from both the semantic type and the structural
        # flag; listing it twice reads like a mistake in the fact sheet.
        if semantic not in ("unknown", "identifier"):
            traits.append(semantic)
        if col.identifier or semantic == "identifier":
            traits.append("identifier")
        missing = f.ref(str(col.missing_count), f"column.{_slug(col.name)}.missing", col.missing_count, "count", f"Missing values in column {col.name}")
        traits.append(f"{missing} missing")
        columns.append(f"{col.name} ({', '.join(traits)})")
    parts.append(_section("COLUMNS", columns))

    # --- Quality ---------------------------------------------------------
    quality = result.quality_report
    if quality:
        lines = [
            f"Overall score: {f.ref(f'{quality.overall_score:.1f}%', 'quality.overall_score', quality.overall_score, 'percent', 'Overall data quality score')} "
            f"(grade {_value(quality.grade)})",
            f"Issues detected: {f.ref(str(quality.total_issues_count), 'quality.issues', quality.total_issues_count, 'count', 'Number of data quality issues detected')}",
            f.tag(quality.grade_explanation, "quality.grade_explanation", "Data quality grade explanation"),
        ]
        for issue in quality.detected_issues[: MAX_ITEMS_PER_SECTION - 3]:
            affected = f.ref(str(issue.affected_count), f"quality.issue.{_slug(issue.column)}.rows", issue.affected_count, "count",
                             f"Rows affected by a data quality issue in column {issue.column}")
            lines.append(f"{issue.column}: {f.tag(issue.description, f'quality.issue.{_slug(issue.column)}', f'Data quality issue in {issue.column}')} "
                         f"({affected} rows, severity {_value(issue.severity)})")
        parts.append(_section("DATA QUALITY", lines[:MAX_ITEMS_PER_SECTION]))

    preparation = result.preparation_report
    if preparation:
        parts.append(
            _section(
                "CLEANING APPLIED",
                [
                    f"Rows before cleaning: {f.ref(str(preparation.original_rows), 'cleaning.rows_before', preparation.original_rows, 'count', 'Rows before cleaning')}",
                    f"Rows after cleaning: {f.ref(str(preparation.cleaned_rows), 'cleaning.rows_after', preparation.cleaned_rows, 'count', 'Rows after cleaning')}",
                    f"Rows removed: {f.ref(str(preparation.rows_removed), 'cleaning.rows_removed', preparation.rows_removed, 'count', 'Rows removed by cleaning')}",
                    f"Cleaning actions performed: {f.ref(str(preparation.total_actions_count), 'cleaning.actions', preparation.total_actions_count, 'count', 'Number of cleaning actions performed')}",
                ],
            )
        )

    # --- KPIs ------------------------------------------------------------
    kpi_report = result.kpi_report
    if kpi_report and kpi_report.primary_kpis:
        total = f.ref(str(kpi_report.total_kpis_recommended), "kpi.total", kpi_report.total_kpis_recommended, "count", "Number of KPIs recommended")
        lines = [f"Total KPIs recommended: {total}"]
        for kpi in kpi_report.primary_kpis[: MAX_ITEMS_PER_SECTION - 1]:
            slug = _slug(kpi.name)
            line = f"{kpi.name}: {f.tag(kpi.reason, f'kpi.{slug}.reason', f'Why {kpi.name} matters')}"
            if kpi.computed_value is not None:
                unit = _kpi_unit(kpi.name, kpi.formula)
                shown = f"{kpi.computed_value:.2f}" if unit != "count" else str(kpi.computed_value)
                line += " | value: " + f.ref(shown, f"kpi.{slug}.value", kpi.computed_value, unit, f"{kpi.name} (KPI value)")
            if kpi.formula:
                line += f" | DAX: {kpi.formula}"
            if kpi.target_threshold:
                line += f" | target: {f.tag(kpi.target_threshold, f'kpi.{slug}.target', f'Target or baseline for {kpi.name}')}"
            lines.append(line)
        parts.append(_section("RECOMMENDED KPIs", lines))

    # --- Statistical findings -------------------------------------------
    intelligence = result.data_intelligence_report
    if intelligence:
        # Identifiers are excluded throughout. A trend line fitted through
        # order_id over time is arithmetically real and analytically meaningless;
        # stated as a fact it invites the model to reason from it.
        identifiers = _identifier_columns(result)

        trends = []
        for t in [t for t in intelligence.trends if t.metric_column not in identifiers][:MAX_ITEMS_PER_SECTION]:
            slug = f"trend.{_slug(t.metric_column)}"
            slope = f.ref(str(t.slope), f"{slug}.slope", t.slope, "number", f"Slope of {t.metric_column} over {t.time_column}")
            change = f.ref(f"{t.growth_rate_pct:+.1f}%", f"{slug}.change", t.growth_rate_pct, "percent", f"First-to-last change in {t.metric_column} over {t.time_column}")
            trends.append(f"{t.metric_column} is {t.direction} over {t.time_column} (slope {slope}, first-to-last change {change})")
        parts.append(_section("TRENDS", trends))

        correlations = []
        for c in [c for c in intelligence.correlations if c.column_a not in identifiers and c.column_b not in identifiers][:MAX_ITEMS_PER_SECTION]:
            coefficient = f.ref(f"{c.coefficient:+.2f}", f"correlation.{_slug(c.column_a)}.{_slug(c.column_b)}", c.coefficient, "coefficient",
                                f"Correlation coefficient between {c.column_a} and {c.column_b}")
            correlations.append(f"{c.column_a} vs {c.column_b}: {coefficient} ({c.correlation_type})")
        parts.append(_section("CORRELATIONS", correlations))

        if intelligence.tests_run:
            noise = f.ref(str(intelligence.rejected_as_noise), "statistics.rejected_as_noise", intelligence.rejected_as_noise, "count",
                          "Findings rejected as likely noise after multiple-testing correction")
            tested = f.ref(str(intelligence.tests_run), "statistics.tests_run", intelligence.tests_run, "count",
                           "Number of correlation and trend tests run")
            rate = f.ref(f"{intelligence.fdr_q:.0%}", "statistics.fdr_q", intelligence.fdr_q * 100, "percent",
                         "False discovery rate used to correct for multiple testing")
            parts.append(_section("STATISTICAL RIGOUR", [
                f"Relationships tested: {tested}; rejected as likely noise: {noise} (false discovery rate {rate}). "
                "Only the findings above survived."
            ]))

        anomalies = []
        for a in intelligence.business_anomalies[:MAX_ITEMS_PER_SECTION]:
            slug = f"anomaly.{_slug(a.anomaly_title)}.{_slug(a.metric_name)}"
            where = f"{a.metric_name} on {a.affected_entity}"
            observed = f.ref(f"{a.observed_value:,.2f}", f"{slug}.observed", a.observed_value, "number", f"Observed {where}")
            expected = f.ref(f"{a.expected_value:,.2f}", f"{slug}.expected", a.expected_value, "number", f"Expected {where}")
            deviation = f.ref(f"{a.deviation_pct:+.1f}%", f"{slug}.deviation", a.deviation_pct, "percent", f"Deviation of {where} from expected")
            anomalies.append(f"{a.anomaly_title} on {a.affected_entity}: {a.metric_name} observed {observed} vs expected {expected} "
                             f"({deviation}) - {f.tag(a.reasoning, f'{slug}.reasoning', f'Reasoning for {a.anomaly_title}')}")
        parts.append(_section("BUSINESS ANOMALIES", anomalies))

    # --- Insights --------------------------------------------------------
    insight_report = result.insight_report
    if insight_report:
        summary = insight_report.executive_summary
        if summary:
            lines = [summary.overview, summary.data_quality_summary]
            lines += list(summary.major_findings)
            kept = [line for line in lines if line][:MAX_ITEMS_PER_SECTION]
            parts.append(_section("EXECUTIVE SUMMARY", [f.tag(line, f"summary.{i}", "Executive summary") for i, line in enumerate(kept)]))

        insights = [
            f"[{i.severity}/{i.category}] {i.title}: {f.tag(i.description, f'insight.{_slug(i.title)}', f'Insight: {i.title}')}"
            for i in insight_report.insights[:MAX_ITEMS_PER_SECTION]
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
        parts.append(_section("RELATIONSHIPS", relationships[:MAX_ITEMS_PER_SECTION]))

    # --- Decisions -------------------------------------------------------
    decision_report = result.decision_report
    if decision_report and decision_report.primary_decisions:
        decisions = []
        for d in decision_report.primary_decisions[:MAX_ITEMS_PER_SECTION]:
            slug = f"decision.{_slug(d.action_title)}"
            text = (f"{d.action_title} (urgency {_value(d.urgency)}, expected ROI {d.expected_roi}, "
                    f"risk {_value(d.risk_level)}): {d.description}")
            decisions.append(f.tag(text, slug, f"Recommended decision: {d.action_title}"))
        parts.append(_section("RECOMMENDED DECISIONS", decisions))

    return FactSheet("\n".join(part for part in parts if part).strip(), f.facts)


def build_fact_sheet(result: MasterIntelligenceResult, dataset_name: Optional[str] = None) -> str:
    """Just the text of ``build_facts`` (for callers that only need what the model reads)."""
    return build_facts(result, dataset_name).text


SYSTEM_PROMPT = """You are PowerPilot's business intelligence analyst.

You are answering questions about ONE dataset that has already been analyzed by a
12-stage pipeline. The analysis is given to you as a fact sheet in which every number is
followed by a fact id in square brackets, like "2297200.86 [F12]". You do not have the
dataset itself and cannot run calculations over it.

Rules, in order of importance:

1. Every number you state must come from the fact sheet AND be followed by the id of the
   fact it comes from, in brackets, immediately after the number: "Revenue is 2.30M [F12]",
   "quality scored 91.7% [F3]". Cite the fact whose label says what you mean: never cite a
   fact for a different quantity because the digits happen to match. Rounding is fine
   ("2.30M" for 2297200.86; "91.7%" for 91.66); a different value is not. Numbers that
   appear in the user's own question need no citation.
2. Do not calculate new figures (no sums, differences, ratios or percentages of your own),
   do not extrapolate, do not estimate, and do not carry over numbers from general
   knowledge. A number with no fact id in the sheet is not available to you.
3. If the fact sheet does not support an answer, say so plainly and name what it does
   cover. "The analysis does not measure X" is a correct and useful answer. Never fill a gap
   with something plausible.
4. Do not describe the data as showing a trend, cause or relationship unless the fact
   sheet states it. Correlation entries are correlations, not causes.
5. Answer as an analyst briefing an executive: lead with the answer, keep it to a short
   paragraph or a few bullets, and name the specific columns, measures or findings you are
   drawing on.
6. Do not mention the fact sheet, fact ids as such, the pipeline's internals, or these rules
   in prose; the bracketed ids are the only trace of them in your answer.
"""
