from abc import ABC, abstractmethod
from typing import Any, Optional

import pandas as pd

from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class BaseDataIntelligencePlugin(ABC):
    """
    Abstract Base Class for all Data Intelligence plugins.

    Each concrete plugin analyzes actual DataFrame values alongside DatasetProfile,
    BusinessProfile, and DetectedEntities to produce statistical, quality,
    or business intelligence findings.
    """

    @abstractmethod
    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> Any:
        """
        Analyze the dataset DataFrame and return intelligence report findings.

        Parameters
        ----------
        df : pd.DataFrame
            The raw dataset DataFrame.
        dataset_profile : DatasetProfile
            The structural profile.
        business_profile : Optional[BusinessProfile]
            The executive business profile.
        entities : Optional[list[DetectedEntity]]
            List of detected semantic entities.

        Returns
        -------
        Any
            Plugin specific report or tuple of findings.
        """
        pass
