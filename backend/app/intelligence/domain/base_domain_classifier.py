from abc import ABC, abstractmethod

from app.models.dataset_profile import DatasetProfile
from app.models.domain_detection_result import DomainDetectionResult


class BaseDomainClassifier(ABC):
    """
    Abstract Base Class for all domain classifier plugins.

    Each concrete domain classifier evaluates a single dataset domain
    (e.g., Retail, Finance, HR, Healthcare, Marketing, Logistics) against
    the semantic entities and structural metadata in a DatasetProfile.
    """

    @abstractmethod
    def classify(self, profile: DatasetProfile) -> DomainDetectionResult:
        """
        Evaluate if a DatasetProfile matches this business domain.

        Parameters
        ----------
        profile : DatasetProfile
            The dataset profile enriched by Schema Analyzer and Entity Detector.

        Returns
        -------
        DomainDetectionResult
            Classification result containing domain enum, confidence score,
            matched entities, missing entities, evidence trail, and reasoning.
        """
        pass
