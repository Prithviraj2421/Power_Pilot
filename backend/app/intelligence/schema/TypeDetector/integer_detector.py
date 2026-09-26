"""Integer type detector plugin."""
from typing import Optional

import pandas as pd

from app.intelligence.schema.TypeDetector.base_detector import BaseDetector
from app.models.type_detection_result import TypeDetectionResult
from app.common.enums import PhysicalType


class IntegerDetector(BaseDetector):
    """Detector for integer columns."""
    
    _MIN_PARSE_RATIO = 0.90

    def detect(self, series: pd.Series) -> Optional[TypeDetectionResult]:
        """Detect if the series matches an integer physical type.
        
        Args:
            series (pd.Series): The pandas Series to analyze.
            
        Returns:
            TypeDetectionResult | None: Detection result if matched, else None.
        """
        valid_series = series.dropna()
        if valid_series.empty:
            return None
            
        total_count = len(valid_series)
        
        # Case 1: Native int dtype
        if pd.api.types.is_integer_dtype(valid_series):
            evidence = (
                "Native pandas integer dtype detected.",
                f"All {total_count} non-null values are integers."
            )
            return TypeDetectionResult(
                physical_type=PhysicalType.INTEGER,
                confidence=1.0,
                evidence=evidence
            )
            
        # Case 2: Float dtype where ALL non-null values have zero fractional part
        if pd.api.types.is_float_dtype(valid_series):
            is_whole = (valid_series % 1 == 0)
            whole_count = is_whole.sum()
            match_ratio = whole_count / total_count
            
            if match_ratio >= 0.95:
                evidence = (
                    "Float column with all whole numbers (likely integers stored with NaN).",
                    f"{whole_count} out of {total_count} values are whole numbers."
                )
                return TypeDetectionResult(
                    physical_type=PhysicalType.INTEGER,
                    confidence=float(match_ratio),
                    evidence=evidence
                )
                
        # Case 3: Object dtype
        if pd.api.types.is_object_dtype(valid_series) or pd.api.types.is_string_dtype(valid_series):
            def can_parse_int(val):
                try:
                    int(str(val).strip())
                    return True
                except (ValueError, TypeError):
                    return False
                    
            parse_success = valid_series.apply(can_parse_int)
            parse_count = parse_success.sum()
            parse_ratio = parse_count / total_count
            
            if parse_ratio >= self._MIN_PARSE_RATIO:
                evidence = (
                    "Parsed string values as integers.",
                    f"{parse_count} out of {total_count} values successfully parsed to int."
                )
                return TypeDetectionResult(
                    physical_type=PhysicalType.INTEGER,
                    confidence=float(parse_ratio),
                    evidence=evidence
                )
                
        return None
