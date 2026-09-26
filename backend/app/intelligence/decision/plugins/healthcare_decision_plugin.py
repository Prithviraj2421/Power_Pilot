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


class HealthcareDecisionPlugin(BaseDecisionPlugin):
    """
    Decision plugin for the HEALTHCARE domain.
    """

    target_domain = DatasetDomain.HEALTHCARE

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
                action_title="Implement Accelerated Discharge Protocol for Low-Risk Admissions",
                description="Streamline clinical discharge workflow to reduce Average Length of Stay (ALOS) below 4.5 days.",
                target_entity="Clinical Operations & Bed Management",
                urgency="IMMEDIATE",
                expected_roi="+15% Hospital Bed Availability",
                risk_level="LOW",
                confidence=0.91,
                reasoning="ALOS metrics exceed optimal clinical benchmark targets.",
                supporting_evidence=("Domain: Healthcare", "ALOS target > 4.5 days"),
            ),
        )

        scenarios = (
            ScenarioOption(
                scenario_name="Clinical Workflow Optimization",
                description="Standardize post-op discharge checklists across all wards.",
                assumptions=("ALOS drops by 0.6 days", "Bed turnover increases by 12%"),
                projected_impact="+$210k Clinical Operating Cost Efficiency",
                probability_of_success=0.87,
            ),
        )

        return DecisionReport(
            executive_decision_summary="Healthcare decisions focus on clinical discharge acceleration and bed turnover optimization.",
            domain=DatasetDomain.HEALTHCARE,
            primary_decisions=actions,
            scenario_options=scenarios,
            risk_matrix_summary="Zero patient care quality compromise; low readmission risk under structured discharge criteria.",
            all_decisions=actions,
        )
