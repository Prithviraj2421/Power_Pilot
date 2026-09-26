from abc import ABC, abstractmethod
from typing import Any, Optional

from app.common.enums import DatasetDomain
from app.models.business_profile import BusinessProfile
from app.models.dashboard_models import DashboardRecommendationReport
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.decision_models import DecisionReport
from app.models.insight_models import InsightReport
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport


class BaseDecisionPlugin(ABC):
    """
    Abstract Base Class for all Decision Engine plugins.

    Each concrete plugin synthesizes all upstream intelligence into high-impact
    executive decision actions, scenario analyses, and risk matrices.
    """

    target_domain: DatasetDomain = DatasetDomain.UNKNOWN

    @abstractmethod
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
        Generate executive decision report for a domain.

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
            Unified decision report containing actions and scenarios.
        """
        pass
