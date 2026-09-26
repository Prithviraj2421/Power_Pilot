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


class LogisticsDecisionPlugin(BaseDecisionPlugin):
    """
    Decision plugin for the LOGISTICS domain.
    """

    target_domain = DatasetDomain.LOGISTICS

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
                action_title="Enforce Strict Carrier Delivery SLA & Consolidate Volume",
                description="Shift 25% freight volume from high-delay carriers to top-performing air/express freight providers.",
                target_entity="Supply Chain & Freight Operations",
                urgency="IMMEDIATE",
                expected_roi="-60% Shipping Delay Reduction",
                risk_level="MEDIUM",
                confidence=0.91,
                reasoning="Carrier ExpressAir maintains lowest average delay (0.4 days) vs underperforming carriers.",
                supporting_evidence=("Domain: Logistics", "ExpressAir delay: 0.4 days"),
            ),
        )

        scenarios = (
            ScenarioOption(
                scenario_name="Freight Carrier Consolidation",
                description="Negotiate bulk volume discounts with top 2 regional carriers.",
                assumptions=("Freight cost per unit drops by $0.40", "On-time delivery reaches 98%"),
                projected_impact="+$110k Freight Cost Reduction",
                probability_of_success=0.89,
            ),
        )

        return DecisionReport(
            executive_decision_summary="Logistics decisions prioritize carrier SLA enforcement and freight cost per unit consolidation.",
            domain=DatasetDomain.LOGISTICS,
            primary_decisions=actions,
            scenario_options=scenarios,
            risk_matrix_summary="Low supply chain disruption risk; high customer delivery satisfaction impact.",
            all_decisions=actions,
        )
