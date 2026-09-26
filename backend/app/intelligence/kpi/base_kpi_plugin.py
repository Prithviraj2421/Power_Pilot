from abc import ABC, abstractmethod
from typing import Any, Optional

import pandas as pd

from app.common.enums import DatasetDomain
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation
from app.models.relationship_models import RelationshipReport


class BaseKPIPlugin(ABC):
    """
    Abstract Base Class for all KPI Recommendation Engine plugins.

    Each concrete plugin evaluates structural profile, business context, data intelligence,
    and relationships to generate domain-aware KPI recommendations.
    """

    target_domain: DatasetDomain = DatasetDomain.UNKNOWN

    @abstractmethod
    def recommend(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        entities: Optional[list[DetectedEntity]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[KPIRecommendation, ...]:
        """
        Generate KPI recommendations for a specific domain.

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
        tuple[KPIRecommendation, ...]
            Tuple of recommended KPI objects.
        """
        pass
