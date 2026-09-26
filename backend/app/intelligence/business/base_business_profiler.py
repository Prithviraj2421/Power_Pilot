from abc import ABC, abstractmethod
from typing import Optional

from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class BaseBusinessProfiler(ABC):
    """
    Abstract Base Class for all business intelligence profiler plugins.

    Each concrete profiler generates executive business understanding for a specific
    domain (e.g. Retail, Finance, HR, Healthcare, Marketing, Logistics, Fallback).
    """

    @abstractmethod
    def profile(
        self,
        dataset_profile: DatasetProfile,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> BusinessProfile:
        """
        Transform technical dataset profile and entities into a BusinessProfile.

        Parameters
        ----------
        dataset_profile : DatasetProfile
            The dataset profile enriched by Schema Analyzer, Entity Detector, and Domain Classifier.
        entities : Optional[list[DetectedEntity]]
            List of detected semantic entities for deep context extraction.

        Returns
        -------
        BusinessProfile
            The executive business understanding containing KPIs, charts, layouts, questions, and insights.
        """
        pass
