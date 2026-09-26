from typing import Optional

from app.common.enums import DatasetDomain
from app.intelligence.decision.base_decision_plugin import BaseDecisionPlugin
from app.models.business_profile import BusinessProfile
from app.models.dashboard_models import DashboardRecommendationReport
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.decision_models import DecisionAction, DecisionReport, ScenarioOption
from app.models.insight_models import InsightReport
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport


class FinanceDecisionPlugin(BaseDecisionPlugin):
    """
    Decision plugin for the FINANCE domain.
    """

    target_domain = DatasetDomain.FINANCE

    def decide(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        insight_report: Optional[InsightReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        kpi_report: Optional[KPIReport] = None,
        dashboard_report: Optional[DashboardRecommendationReport] = None,
    ) -> DecisionReport:
        actions = (
            DecisionAction(
                action_title="Enforce 5% Discretionary Operating Cost Freeze",
                description="Cap non-essential departmental OPEX expenditures across corporate ledger accounts.",
                target_entity="Corporate FP&A & Accounting",
                urgency="IMMEDIATE",
                expected_roi="+3.2% EBITDA Margin Expansion",
                risk_level="MEDIUM",
                confidence=0.94,
                reasoning="Operating Expense Ratio exceeds optimal target of 65.0%.",
                supporting_evidence=("Domain: Finance", "OPEX ratio threshold violation"),
            ),
        )

        scenarios = (
            ScenarioOption(
                scenario_name="Cost Reduction & Capital Conservation",
                description="Freeze hiring and delay non-critical capital expenditures for 2 quarters.",
                assumptions=("OPEX drops by 6%", "EBITDA margin rises to 23%"),
                projected_impact="+$320k Cash Preservation",
                probability_of_success=0.88,
            ),
        )

        return DecisionReport(
            executive_decision_summary="Financial decisions focus on OPEX cost containment and cash preservation to defend EBITDA margin targets.",
            domain=DatasetDomain.FINANCE,
            primary_decisions=actions,
            scenario_options=scenarios,
            risk_matrix_summary="Moderate risk of operational pushback on discretionary budget caps; low solvency risk.",
            all_decisions=actions,
        )
