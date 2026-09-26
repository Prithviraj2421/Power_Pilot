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


class FallbackDecisionPlugin(BaseDecisionPlugin):
    """
    Fallback decision plugin for UNKNOWN or unclassified domains.
    """

    target_domain = DatasetDomain.UNKNOWN

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
                action_title=f"Execute Automated Data Cleaning on '{dataset_profile.dataset_name}'",
                description="Clean missing values, duplicate rows, and outlier values across dataset columns.",
                target_entity="Data Engineering & Governance",
                urgency="SHORT_TERM",
                expected_roi="+100% Data Quality Health Score",
                risk_level="LOW",
                confidence=0.85,
                reasoning="Generic exploratory dataset requires data hygiene before strategic decision-making.",
                supporting_evidence=("Domain: Unknown", f"Dataset: {dataset_profile.dataset_name}"),
            ),
        )

        scenarios = (
            ScenarioOption(
                scenario_name="Standard Data Cleaning Protocol",
                description="Apply automated median imputation and duplicate row removal.",
                assumptions=("Zero data loss", "100% downstream pipeline compatibility"),
                projected_impact="Clean structured dataset for analytics",
                probability_of_success=0.95,
            ),
        )

        return DecisionReport(
            executive_decision_summary="General operational decision support focusing on data quality hygiene.",
            domain=DatasetDomain.UNKNOWN,
            primary_decisions=actions,
            scenario_options=scenarios,
            risk_matrix_summary="Low operational risk.",
            all_decisions=actions,
        )
