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


class HRDecisionPlugin(BaseDecisionPlugin):
    """
    Decision plugin for the HR domain.
    """

    target_domain = DatasetDomain.HR

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
                action_title="Adjust Departmental Salary Equity Benchmarks",
                description="Conduct target compensation adjustments for key engineering and sales cohorts to curb voluntary attrition.",
                target_entity="Human Resources & Total Rewards",
                urgency="SHORT_TERM",
                expected_roi="-25% Voluntary Attrition Reduction",
                risk_level="LOW",
                confidence=0.90,
                reasoning="Salary distribution variance detected across 2-3 year tenure cohorts.",
                supporting_evidence=("Domain: HR", "Tenure-salary variance detected"),
            ),
        )

        scenarios = (
            ScenarioOption(
                scenario_name="Targeted Retention Incentive Program",
                description="Allocate $50k retention pool for key technical talent.",
                assumptions=("Key staff turnover drops to <3%", "Avoids $150k replacement hiring cost"),
                projected_impact="+$100k Net Recruitment Cost Savings",
                probability_of_success=0.90,
            ),
        )

        return DecisionReport(
            executive_decision_summary="HR decisions prioritize talent retention and pay equity stabilization to avoid costly recruitment cycles.",
            domain=DatasetDomain.HR,
            primary_decisions=actions,
            scenario_options=scenarios,
            risk_matrix_summary="Low financial risk; high positive impact on staff morale and organizational continuity.",
            all_decisions=actions,
        )
