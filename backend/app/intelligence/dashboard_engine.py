from typing import Optional

from app.common.enums import DatasetDomain
from app.intelligence.dashboard.base_dashboard_plugin import BaseDashboardPlugin
from app.intelligence.dashboard.plugins import DASHBOARD_RECOMMENDATION_REGISTRY, FallbackDashboardPlugin
from app.models.business_profile import BusinessProfile
from app.models.dashboard_models import DashboardRecommendationReport
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import InsightReport
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport


class DashboardEngine:
    """
    Facade orchestrating dashboard layout generation across registered domain plugins.

    Selects the plugin matching DatasetProfile.detected_domain and builds a DashboardRecommendationReport.
    """

    def __init__(self) -> None:
        """Initialize domain dashboard plugins lookup map."""
        self._plugins: dict[DatasetDomain, BaseDashboardPlugin] = {}
        self._fallback = FallbackDashboardPlugin()

        for plugin_cls in DASHBOARD_RECOMMENDATION_REGISTRY:
            plugin = plugin_cls()
            target_domain = getattr(plugin, "target_domain", None)
            if target_domain and isinstance(target_domain, DatasetDomain):
                self._plugins[target_domain] = plugin

    def recommend(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        insight_report: Optional[InsightReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        kpi_report: Optional[KPIReport] = None,
    ) -> DashboardRecommendationReport:
        """
        Generate multi-tab dashboard recommendation layout for a dataset.

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

        Returns
        -------
        DashboardRecommendationReport
            Unified multi-tab dashboard recommendation report.
        """
        domain = getattr(dataset_profile, "detected_domain", DatasetDomain.UNKNOWN)
        plugin = self._plugins.get(domain, self._fallback)

        try:
            return plugin.recommend(dataset_profile, business_profile, intelligence_report, insight_report, relationship_report, kpi_report)
        except Exception:
            return self._fallback.recommend(dataset_profile, business_profile, intelligence_report, insight_report, relationship_report, kpi_report)
