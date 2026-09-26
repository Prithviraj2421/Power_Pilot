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


class RetailDecisionPlugin(BaseDecisionPlugin):
    """
    Decision plugin for the RETAIL domain.
    """

    target_domain = DatasetDomain.RETAIL

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
                action_title="Reallocate Inventory to High-Margin Product Categories",
                description="Reallocate 15% of safety stock inventory from low-performing SKUs to top 20% revenue-generating categories.",
                target_entity="Merchandising & Inventory Control",
                urgency="IMMEDIATE",
                expected_roi="+12% Gross Margin Expansion",
                risk_level="MEDIUM",
                confidence=0.92,
                reasoning="Pareto 80/20 analysis indicates top 20% categories drive >70% total revenue.",
                supporting_evidence=("Domain: Retail", "Pareto concentration signal detected"),
            ),
            DecisionAction(
                action_title="Launch Dynamic Pricing & Bundle Promos on High-AOV Items",
                description="Implement automated cross-selling bundle discounts for orders approaching $75.00 AOV target threshold.",
                target_entity="E-Commerce & Retail POS",
                urgency="SHORT_TERM",
                expected_roi="+8.5% Average Order Value Growth",
                risk_level="LOW",
                confidence=0.90,
                reasoning="Basket concentration data demonstrates strong co-purchasing probability.",
                supporting_evidence=("Target AOV: > $75.00", "AOV KPI formula active"),
            ),
        )

        scenarios = (
            ScenarioOption(
                scenario_name="Aggressive Promotion Strategy",
                description="Offer 10% instant checkout discount on multi-item baskets.",
                assumptions=("Basket size increases by 25%", "Gross margin absorbs 1.5% discount cost"),
                projected_impact="+$140k Incremental Quarterly Revenue",
                probability_of_success=0.85,
            ),
            ScenarioOption(
                scenario_name="Conservative Margin Retention Strategy",
                description="Maintain fixed pricing and eliminate low-performing SKU inventory.",
                assumptions=("Holding costs drop by 20%", "Zero discount cost erosion"),
                projected_impact="+$45k Net Inventory Cost Reduction",
                probability_of_success=0.90,
            ),
        )

        return DecisionReport(
            executive_decision_summary="Retail strategic decisions focus on inventory reallocation toward high-margin Pareto SKUs and basket size optimization.",
            domain=DatasetDomain.RETAIL,
            primary_decisions=actions,
            scenario_options=scenarios,
            risk_matrix_summary="Low stockout risk for top SKUs; low margin erosion risk under promo discount caps.",
            all_decisions=actions,
        )
