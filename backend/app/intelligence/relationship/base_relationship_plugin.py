from abc import ABC, abstractmethod
from typing import Any, Optional

import pandas as pd

from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.relationship_models import EntityRelationship


class BaseRelationshipPlugin(ABC):
    """
    Abstract Base Class for all Relationship Engine plugins.

    Each concrete plugin discovers structural, statistical, or semantic relationships
    across dataset columns.
    """

    @abstractmethod
    def analyze(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        entities: Optional[list[DetectedEntity]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> tuple[EntityRelationship, ...]:
        """
        Analyze dataset metadata and return identified EntityRelationship objects.

        Parameters
        ----------
        dataset_profile : DatasetProfile
            The structural profile.
        business_profile : Optional[BusinessProfile]
            The executive business profile.
        intelligence_report : Optional[DataIntelligenceReport]
            The data intelligence report.
        entities : Optional[list[DetectedEntity]]
            List of detected semantic entities.
        df : Optional[pd.DataFrame]
            Optional raw DataFrame.

        Returns
        -------
        tuple[EntityRelationship, ...]
            Tuple of identified relationship objects.
        """
        pass
