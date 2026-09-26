from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult


class BaseEntityDetector(ABC):
    """
    Abstract Base Class for all semantic entity detector plugins.

    Each concrete detector evaluates a single semantic entity type
    (e.g., Customer, Product, Revenue) against a column's profile and optional
    series data.
    """

    @abstractmethod
    def detect(
        self,
        column: ColumnProfile,
        series: Optional[pd.Series] = None,
    ) -> Optional[EntityDetectionResult]:
        """
        Evaluate if a column represents this entity type.

        Parameters
        ----------
        column : ColumnProfile
            The structural profile of the column.
        series : Optional[pd.Series]
            The raw pandas Series for deep content/pattern inspection.

        Returns
        -------
        Optional[EntityDetectionResult]
            Result if this detector fires above minimum confidence threshold;
            otherwise None.
        """
        pass
