from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.plugins import KPI_RECOMMENDATION_REGISTRY, FallbackKPIPlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport


class KPIEngine:
    """
    Facade orchestrating KPI recommendation generation across registered domain plugins.

    Selects the plugin matching DatasetProfile.detected_domain, ranks KPIs, and builds a KPIReport.
    """

    def __init__(self) -> None:
        """Initialize domain plugins lookup map."""
        self._plugins: dict[DatasetDomain, BaseKPIPlugin] = {}
        self._fallback = FallbackKPIPlugin()

        for plugin_cls in KPI_RECOMMENDATION_REGISTRY:
            plugin = plugin_cls()
            target_domain = getattr(plugin, "target_domain", None)
            if target_domain and isinstance(target_domain, DatasetDomain):
                self._plugins[target_domain] = plugin

    def recommend(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        entities: Optional[list[DetectedEntity]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> KPIReport:
        """
        Generate ranked KPI recommendations for a dataset.

        Parameters
        ----------
        dataset_profile : DatasetProfile
            The structural profile.
        business_profile : Optional[BusinessProfile]
            The executive business profile.
        intelligence_report : Optional[DataIntelligenceReport]
            The data intelligence report.
        relationship_report : Optional[RelationshipReport]
            The relationship report.
        entities : Optional[list[DetectedEntity]]
            List of detected semantic entities.
        df : Optional[pd.DataFrame]
            Optional raw DataFrame.

        Returns
        -------
        KPIReport
            Unified KPI recommendation report.
        """
        domain = getattr(dataset_profile, "detected_domain", DatasetDomain.UNKNOWN)
        plugin = self._plugins.get(domain, self._fallback)

        try:
            raw_kpis = plugin.recommend(dataset_profile, business_profile, intelligence_report, relationship_report, entities, df)
        except Exception:
            raw_kpis = self._fallback.recommend(dataset_profile, business_profile, intelligence_report, relationship_report, entities, df)

        kpis_list = list(raw_kpis) if isinstance(raw_kpis, (list, tuple)) else []

        prio_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
        kpis_list.sort(key=lambda k: (prio_order.get(k.priority, 2), -k.confidence))

        primary_kpis = tuple(kpis_list[:3])
        secondary_kpis = tuple(kpis_list[3:])

        return KPIReport(
            primary_kpis=primary_kpis,
            secondary_kpis=secondary_kpis,
            all_kpis=tuple(kpis_list),
            domain=domain,
            total_kpis_recommended=len(kpis_list),
        )
