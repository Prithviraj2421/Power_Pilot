"""Boolean type detector plugin."""
from typing import Optional

import pandas as pd

from app.intelligence.schema.TypeDetector.base_detector import BaseDetector
from app.models.type_detection_result import TypeDetectionResult
from app.common.enums import PhysicalType
from app.common.constants import BOOLEAN_VALUES


class BooleanDetector(BaseDetector):
    """Detector for boolean columns."""
    
    _MIN_BOOLEAN_MATCH_RATIO = 0.95

    def detect(self, series: pd.Series) -> Optional[TypeDetectionResult]:
        """Detect if the series matches a boolean physical type.
        
        Args:
            series (pd.Series): The pandas Series to analyze.
            
        Returns:
            TypeDetectionResult | None: Detection result if matched, else None.
        """
        valid_series = series.dropna()
        if valid_series.empty:
            return None
            
        total_count = len(valid_series)
        
        # Convert all to lowercase string, then check if in BOOLEAN_VALUES
        matched_values = valid_series.astype(str).str.lower().isin(BOOLEAN_VALUES)
        match_count = matched_values.sum()
        
        match_ratio = match_count / total_count
        if match_ratio >= self._MIN_BOOLEAN_MATCH_RATIO:
            # Find unique matched tokens for evidence
            found_tokens = valid_series[matched_values].astype(str).str.lower().unique()
            evidence = (
                f"Checked {total_count} non-null values.",
                f"{match_count} values matched boolean tokens.",
                f"Found boolean tokens: {', '.join(found_tokens)}."
            )
            return TypeDetectionResult(
                physical_type=PhysicalType.BOOLEAN,
                confidence=float(match_ratio),
                evidence=evidence
            )
            
        return None
