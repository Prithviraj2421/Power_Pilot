from abc import ABC, abstractmethod
import pandas as pd

from app.models.type_detection_result import TypeDetectionResult


class BaseDetector(ABC):
    """Base class for all physical type detectors."""

    @abstractmethod
    def detect(
        self,
        series: pd.Series,
    ) -> TypeDetectionResult | None:
        """
        Returns a detection result if this detector
        recognizes the column.

        Otherwise returns None.
        """