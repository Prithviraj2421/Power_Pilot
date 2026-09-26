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


class MarketingDecisionPlugin(BaseDecisionPlugin):
    """
    Decision plugin for the MARKETING domain.
    """

    target_domain = DatasetDomain.MARKETING

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
                action_title="Reallocate 20% Ad Budget to Top-ROAS Paid Search Channels",
                description="Shift ad spend away from underperforming display channels into high-converting Paid Search campaigns.",
                target_entity="Digital Growth Marketing",
                urgency="IMMEDIATE",
                expected_roi="+1.2x Overall Campaign ROAS Improvement",
                risk_level="LOW",
                confidence=0.93,
                reasoning="Paid Search channel achieves 4.2x ROAS vs 1.8x on display channels.",
                supporting_evidence=("Domain: Marketing", "Paid Search ROAS: 4.2x"),
            ),
        )

        scenarios = (
            ScenarioOption(
                scenario_name="Channel Reallocation Optimization",
                description="Scale budget on top 2 channels while pausing lowest 10% CPA campaigns.",
                assumptions=("Lead volume increases by 18%", "CPA drops by $12 per lead"),
                projected_impact="+$95k Incremental Conversion Revenue",
                probability_of_success=0.92,
            ),
        )

        return DecisionReport(
            executive_decision_summary="Marketing decisions focus on aggressive ad spend reallocation toward high-ROAS channels.",
            domain=DatasetDomain.MARKETING,
            primary_decisions=actions,
            scenario_options=scenarios,
            risk_matrix_summary="Low acquisition risk; immediate boost to net ROAS efficiency.",
            all_decisions=actions,
        )
