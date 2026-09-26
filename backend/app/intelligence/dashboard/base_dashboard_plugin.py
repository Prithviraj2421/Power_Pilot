from abc import ABC, abstractmethod
from typing import Any, Optional

from app.common.enums import DatasetDomain
from app.models.business_profile import BusinessProfile
from app.models.dashboard_models import DashboardRecommendationReport
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.insight_models import InsightReport
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport


class BaseDashboardPlugin(ABC):
    """
    Abstract Base Class for all Dashboard Recommendation Engine plugins.

    Each concrete plugin designs a multi-tab visual dashboard layout complete with
    widget grid configurations, scorecard cards, charts, and filter controls.
    """

    target_domain: DatasetDomain = DatasetDomain.UNKNOWN

    @abstractmethod
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
        Recommend multi-tab dashboard layout for a domain.

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
        pass
