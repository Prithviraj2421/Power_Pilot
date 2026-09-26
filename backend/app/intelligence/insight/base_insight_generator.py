from abc import ABC, abstractmethod
from typing import Any, Optional

import pandas as pd

from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile


class BaseInsightGenerator(ABC):
    """
    Abstract Base Class for all Insight Generator plugins.

    Each concrete generator analyzes technical DatasetProfile, executive BusinessProfile,
    and deep DataIntelligenceReport (optionally with raw DataFrame) to produce explainable Insight objects.
    """

    @abstractmethod
    def generate(
        self,
        dataset_profile: DatasetProfile,
        business_profile: BusinessProfile,
        intelligence_report: DataIntelligenceReport,
        df: Optional[pd.DataFrame] = None,
    ) -> Any:
        """
        Generate insights or executive summary.

        Parameters
        ----------
        dataset_profile : DatasetProfile
            The structural profile.
        business_profile : BusinessProfile
            The executive business profile.
        intelligence_report : DataIntelligenceReport
            The data intelligence report.
        df : Optional[pd.DataFrame]
            Optional raw dataset DataFrame.

        Returns
        -------
        Any
            Tuple of Insight objects or ExecutiveSummary.
        """
        pass
