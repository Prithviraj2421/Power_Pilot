from typing import Optional

from app.common.enums import DatasetDomain
from app.intelligence.decision.base_decision_plugin import BaseDecisionPlugin
from app.intelligence.decision.plugins import DECISION_ENGINE_REGISTRY, FallbackDecisionPlugin
from app.models.business_profile import BusinessProfile
from app.models.dashboard_models import DashboardRecommendationReport
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.decision_models import DecisionReport
from app.models.insight_models import InsightReport
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport


class DecisionEngine:
    """
    Facade orchestrating executive decision generation across registered domain plugins.

    Selects the plugin matching DatasetProfile.detected_domain and builds a DecisionReport.
    """

    def __init__(self) -> None:
        """Initialize domain decision plugins lookup map."""
        self._plugins: dict[DatasetDomain, BaseDecisionPlugin] = {}
        self._fallback = FallbackDecisionPlugin()

        for plugin_cls in DECISION_ENGINE_REGISTRY:
            plugin = plugin_cls()
            target_domain = getattr(plugin, "target_domain", None)
            if target_domain and isinstance(target_domain, DatasetDomain):
                self._plugins[target_domain] = plugin

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
        """
        Generate executive decision actions and scenario analysis for a dataset.

        Parameters
        ----------
        dataset_profile : DatasetProfile
            The structural profile.
        business_profile : Optional[BusinessProfile]
            The executive business profile.
        intelligence_report : Optional[DataIntelligenceReport]
            The data intelligence report.
        insight_report : Optional[InsightReport]
            The insight report.
        relationship_report : Optional[RelationshipReport]
            The relationship report.
        kpi_report : Optional[KPIReport]
            The KPI report.
        dashboard_report : Optional[DashboardRecommendationReport]
            The dashboard recommendation report.

        Returns
        -------
        DecisionReport
            Unified decision report containing actions, scenarios, and risk matrix.
        """
        domain = getattr(dataset_profile, "detected_domain", DatasetDomain.UNKNOWN)
        plugin = self._plugins.get(domain, self._fallback)

        try:
            return plugin.decide(
                dataset_profile, business_profile, intelligence_report, insight_report, relationship_report, kpi_report, dashboard_report
            )
        except Exception:
            return self._fallback.decide(
                dataset_profile, business_profile, intelligence_report, insight_report, relationship_report, kpi_report, dashboard_report
            )
