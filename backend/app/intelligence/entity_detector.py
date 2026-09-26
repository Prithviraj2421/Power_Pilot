"""
Entity Detector module facade for PowerPilot.

Analyzes column profiles and raw DataFrames to identify business entities
such as Customer, Product, Revenue, Profit, Cost, Quantity, Date, Region, Employee,
and Identifier.
"""

from typing import Optional

import pandas as pd

from app.common.enums import SemanticType
from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.intelligence.entity.detectors import ENTITY_DETECTOR_REGISTRY
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.entity_detection_result import EntityDetectionResult


class EntityDetector:
    """
    Facade orchestrating semantic entity detection across dataset columns.

    Evaluates registered entity detector plugins for each column profile,
    selects the highest confidence prediction exceeding the minimum threshold,
    updates column profiles, and returns a list of DetectedEntity objects.
    """

    _MIN_CONFIDENCE_THRESHOLD: float = 0.35

    def __init__(self) -> None:
        """Initialize all registered entity detector plugins."""
        self._detectors: list[BaseEntityDetector] = [
            detector_cls() for detector_cls in ENTITY_DETECTOR_REGISTRY
        ]

    def detect(
        self,
        profile: DatasetProfile,
        df: Optional[pd.DataFrame] = None,
    ) -> list[DetectedEntity]:
        """
        Detect semantic business entities for all columns in a DatasetProfile.

        Parameters
        ----------
        profile : DatasetProfile
            The dataset profile produced by the Schema Analyzer.
        df : Optional[pd.DataFrame]
            Optional raw DataFrame for deep sample value inspection.

        Returns
        -------
        list[DetectedEntity]
            List of detected semantic entities with confidence scores and evidence.
        """
        detected_entities: list[DetectedEntity] = []

        for column in profile.columns:
            series = df[column.name] if df is not None and column.name in df.columns else None

            best_result: Optional[EntityDetectionResult] = self._detect_column_entity(
                column, series
            )

            if best_result and best_result.confidence >= self._MIN_CONFIDENCE_THRESHOLD:
                column.semantic_type = best_result.semantic_type
                column.confidence = best_result.confidence
                column.metadata["entity_evidence"] = list(best_result.evidence)

                detected_entities.append(
                    DetectedEntity(
                        column_name=column.name,
                        entity_type=best_result.semantic_type.value,
                        confidence=best_result.confidence,
                        reason=best_result.reason,
                    )
                )
            else:
                column.semantic_type = SemanticType.UNKNOWN

        return detected_entities

    def _detect_column_entity(
        self,
        column,
        series: Optional[pd.Series],
    ) -> Optional[EntityDetectionResult]:
        """
        Run all detectors on a single column and select the highest confidence match.

        Parameters
        ----------
        column : ColumnProfile
            The column profile.
        series : Optional[pd.Series]
            Series data if available.

        Returns
        -------
        Optional[EntityDetectionResult]
            The best detection result, or None if no detector fired.
        """
        results: list[EntityDetectionResult] = []

        for detector in self._detectors:
            try:
                res = detector.detect(column, series)
                if res is not None:
                    results.append(res)
            except Exception:
                # Individual detector failures should not break the pipeline
                continue

        if not results:
            return None

        # Return the highest confidence result
        return max(results, key=lambda r: r.confidence)
