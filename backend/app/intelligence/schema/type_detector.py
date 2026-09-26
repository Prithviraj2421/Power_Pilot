"""
TypeDetector orchestrator.

Runs all registered type detector plugins against a pandas Series
and returns the highest-confidence detection result. Uses the
plugin registry from the TypeDetector package for detection order.
"""

import pandas as pd

from app.common.enums import PhysicalType
from app.intelligence.schema.TypeDetector import DETECTOR_PRIORITY
from app.intelligence.schema.TypeDetector.base_detector import BaseDetector
from app.models.type_detection_result import TypeDetectionResult


class TypeDetector:
    """
    Orchestrates physical type detection by running all registered
    detector plugins and selecting the best result.

    The orchestrator follows a "highest confidence wins" strategy:
    all detectors are run, and the result with the highest confidence
    score is returned. If no detector matches, a fallback UNKNOWN
    result is returned.

    The detection priority order is defined in the TypeDetector
    package registry (``DETECTOR_PRIORITY``). In case of tied
    confidence scores, the detector earlier in the priority order wins.
    """

    def __init__(self) -> None:
        """Initialize with all registered detectors in priority order."""
        self._detectors: list[BaseDetector] = [
            detector_cls() for detector_cls in DETECTOR_PRIORITY
        ]

    def detect(self, series: pd.Series) -> TypeDetectionResult:
        """
        Detect the physical type of a pandas Series.

        Runs every registered detector and returns the result
        with the highest confidence. Ties are broken by detection
        priority (earlier detector wins).

        Parameters
        ----------
        series : pd.Series
            The column data to analyze.

        Returns
        -------
        TypeDetectionResult
            The best detection result. If no detector matches,
            returns a result with PhysicalType.UNKNOWN and
            confidence 0.0.
        """
        if series.dropna().empty:
            return self._unknown_result(
                "Column is entirely null or empty"
            )

        results: list[TypeDetectionResult] = []

        for detector in self._detectors:
            result = detector.detect(series)
            if result is not None:
                results.append(result)

        if not results:
            return self._unknown_result(
                "No detector recognized this column"
            )

        # Highest confidence wins; priority order preserved by
        # stable sort on equal confidence values
        return max(results, key=lambda r: r.confidence)

    @staticmethod
    def _unknown_result(reason: str) -> TypeDetectionResult:
        """
        Produce a fallback result for unrecognizable columns.

        Parameters
        ----------
        reason : str
            Human-readable explanation of why detection failed.

        Returns
        -------
        TypeDetectionResult
            Result with PhysicalType.UNKNOWN and confidence 0.0.
        """
        return TypeDetectionResult(
            physical_type=PhysicalType.UNKNOWN,
            confidence=0.0,
            evidence=(reason,),
        )