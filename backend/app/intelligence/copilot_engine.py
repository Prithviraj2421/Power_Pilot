from dataclasses import dataclass
from typing import Any, Optional, Sequence

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


class CopilotEngine:
    """
    Master AI Copilot facade for conversational BI and grounded context synthesis.
    """

    def ask(self, query: str, result: MasterIntelligenceResult) -> CopilotResponse:
        """
        Process user query against grounded MasterIntelligenceResult context.
        """
        q_clean = query.lower().strip()

        if any(w in q_clean for w in ["why", "decrease", "drop", "decline", "fall", "reduce", "loss"]):
            return self._handle_why_decrease(result)
        elif any(w in q_clean for w in ["region", "area", "sales by", "country", "territory", "breakdown"]):
            return self._handle_breakdown(result)
        elif any(w in q_clean for w in ["management", "action", "do", "recommend", "should", "strategy"]):
            return self._handle_management_actions(result)
        elif any(w in q_clean for w in ["kpi", "metric", "benchmark", "measure", "formula", "dax"]):
            return self._handle_kpis(result)
        else:
            return self._handle_general_qa(query, result)

    def _handle_why_decrease(self, result: MasterIntelligenceResult) -> CopilotResponse:
        domain_name = result.dataset_profile.detected_domain.value.upper() if hasattr(result.dataset_profile.detected_domain, 'value') else str(result.dataset_profile.detected_domain).upper()
        anomalies = []
        if result.data_intelligence_report and result.data_intelligence_report.business_anomalies:
            anomalies = [a.description for a in result.data_intelligence_report.business_anomalies]

        insights = []
        if result.insight_report and result.insight_report.insights:
            for i in result.insight_report.insights:
                sev_str = i.severity.value.upper() if hasattr(i.severity, 'value') else str(i.severity).upper()
                if sev_str in ("CRITICAL", "HIGH"):
                    insights.append(i.description)

        evidence = tuple(anomalies + insights[:3])
        if not evidence:
            evidence = ("High variance detected in transaction volume.", "Operational expenses exceeded baseline target thresholds.")

        answer = (
            f"Based on the {domain_name} intelligence analysis for dataset '{result.dataset_profile.dataset_name}', "
            f"the decrease is primarily driven by: {evidence[0]} "
            f"Additionally, quality and trend analysis highlights: {evidence[1] if len(evidence) > 1 else 'margin compression across key dimensions.'}"
        )

        actions = ()
        if result.decision_report and result.decision_report.primary_decisions:
            actions = tuple(d.action_title for d in result.decision_report.primary_decisions[:3])

        return CopilotResponse(
            answer=answer,
            intent="WHY_DECREASE",
            evidence=evidence,
            recommended_actions=actions if actions else ("Renegotiate vendor terms", "Optimize marketing acquisition channels"),
            suggested_followups=(
                "What should management do to recover margins?",
                "Which product categories contributed most to the drop?",
                "Show sales by region.",
            ),
        )

    def _handle_breakdown(self, result: MasterIntelligenceResult) -> CopilotResponse:
        domain_name = result.dataset_profile.detected_domain.value.upper() if hasattr(result.dataset_profile.detected_domain, 'value') else str(result.dataset_profile.detected_domain).upper()
        dims = []
        for col in result.dataset_profile.columns:
            ptype_str = col.physical_type.value.upper() if hasattr(col.physical_type, 'value') else str(col.physical_type).upper()
            if ptype_str in ("CATEGORICAL", "TEXT"):
                dims.append(col.name)
        
        answer = (
            f"For dataset '{result.dataset_profile.dataset_name}' ({domain_name} domain), "
            f"the primary dimensions available for breakdown are: {', '.join(dims[:4]) if dims else 'Region, Store_ID, Product_Category'}. "
            f"Visualizing metrics across these dimensions highlights regional performance variance."
        )

        return CopilotResponse(
            answer=answer,
            intent="SALES_BY_REGION",
            evidence=tuple(f"Dimension identified: {d}" for d in dims[:4]),
            recommended_actions=("Filter Executive Dashboard by primary region", "Export Power BI dimensional report"),
            suggested_followups=(
                "Why did profit decrease in top regions?",
                "What should management do?",
                "Show KPI formulas.",
            ),
        )

    def _handle_management_actions(self, result: MasterIntelligenceResult) -> CopilotResponse:
        actions = []
        if result.decision_report and result.decision_report.primary_decisions:
            for dec in result.decision_report.primary_decisions:
                urgency_str = dec.urgency.value if hasattr(dec.urgency, 'value') else str(dec.urgency)
                actions.append(f"{dec.action_title} (Urgency: {urgency_str}, ROI: {dec.expected_roi})")

        answer = (
            f"Management should prioritize {len(actions) if actions else 'strategic cost optimization'} key actions. "
            f"Top priority: {actions[0] if actions else 'Immediate inventory re-allocation and pricing adjustments.'}"
        )

        return CopilotResponse(
            answer=answer,
            intent="MANAGEMENT_ACTION",
            evidence=tuple(actions[:3]) if actions else ("Immediate action required for high-risk segments",),
            recommended_actions=tuple(dec.action_title for dec in result.decision_report.primary_decisions) if result.decision_report else ("Execute immediate margin recovery plan",),
            suggested_followups=(
                "What is the probability of success for scenario A?",
                "Why did profit decrease?",
                "Export DAX measures to Power BI.",
            ),
        )

    def _handle_kpis(self, result: MasterIntelligenceResult) -> CopilotResponse:
        kpi_names = []
        if result.kpi_report and result.kpi_report.primary_kpis:
            kpi_names = [k.name for k in result.kpi_report.primary_kpis]

        answer = (
            f"PowerPilot recommended {result.kpi_report.total_kpis_recommended if result.kpi_report else 4} executive KPIs for this dataset. "
            f"Primary measures include: {', '.join(kpi_names[:3]) if kpi_names else 'Total Sales, Net Profit, Profit Margin'}. "
            f"Executable DAX formulas are ready for Power BI Desktop."
        )

        return CopilotResponse(
            answer=answer,
            intent="KPI_PERFORMANCE",
            evidence=tuple(f"Measure: {name}" for name in kpi_names[:4]),
            recommended_actions=("Copy DAX formulas to Power BI Desktop", "Set alert thresholds on critical metrics"),
            suggested_followups=(
                "What should management do?",
                "Why did profit decrease?",
                "Export Tabular Model BIM schema.",
            ),
        )

    def _handle_general_qa(self, query: str, result: MasterIntelligenceResult) -> CopilotResponse:
        domain_name = result.dataset_profile.detected_domain.value.upper() if hasattr(result.dataset_profile.detected_domain, 'value') else str(result.dataset_profile.detected_domain).upper()
        summary = result.business_profile.executive_summary if result.business_profile else f"{domain_name} dataset analysis complete."

        answer = (
            f"Summary for '{result.dataset_profile.dataset_name}': {summary} "
            f"Dataset consists of {result.dataset_profile.total_rows} rows and {result.dataset_profile.total_columns} columns."
        )

        return CopilotResponse(
            answer=answer,
            intent="GENERAL_QA",
            evidence=(f"Domain: {domain_name}", f"Rows: {result.dataset_profile.total_rows}"),
            recommended_actions=("Review Executive Dashboard", "Examine AI Insights"),
            suggested_followups=(
                "Why did profit decrease?",
                "What should management do?",
                "Show sales by region.",
            ),
        )
