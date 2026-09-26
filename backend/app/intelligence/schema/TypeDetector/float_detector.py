"""Float type detector plugin."""
from typing import Optional

import pandas as pd

from app.intelligence.schema.TypeDetector.base_detector import BaseDetector
from app.models.type_detection_result import TypeDetectionResult
from app.common.enums import PhysicalType


class FloatDetector(BaseDetector):
    """Detector for float columns."""
    
    _MIN_PARSE_RATIO = 0.90

    def detect(self, series: pd.Series) -> Optional[TypeDetectionResult]:
        """Detect if the series matches a float physical type.
        
        Args:
            series (pd.Series): The pandas Series to analyze.
            
        Returns:
            TypeDetectionResult | None: Detection result if matched, else None.
        """
        valid_series = series.dropna()
        if valid_series.empty:
            return None
            
        total_count = len(valid_series)
        
        # Case 1: Native float dtype
        if pd.api.types.is_float_dtype(valid_series):
            has_fractional = (valid_series % 1 != 0)
            fractional_count = has_fractional.sum()
            
            if fractional_count == 0:
                # All values are whole numbers, let IntegerDetector handle
                return None
                
            evidence = (
                "Native pandas float dtype detected.",
                f"Found {fractional_count} out of {total_count} values with fractional parts."
            )
            return TypeDetectionResult(
                physical_type=PhysicalType.FLOAT,
                confidence=1.0,
                evidence=evidence
            )
            
        # Case 2: Object dtype
        if pd.api.types.is_object_dtype(valid_series) or pd.api.types.is_string_dtype(valid_series):
            parsed_series = pd.to_numeric(valid_series, errors='coerce')
            valid_parsed = parsed_series.dropna()
            parse_count = len(valid_parsed)
            
            if parse_count == 0:
                return None
                
            parse_ratio = parse_count / total_count
            
            has_fractional = (valid_parsed % 1 != 0)
            fractional_count = has_fractional.sum()
            
            if parse_ratio >= self._MIN_PARSE_RATIO and fractional_count > 0:
                evidence = (
                    "Parsed string values as floats.",
                    f"{parse_count} out of {total_count} values successfully parsed to numeric.",
                    f"Found {fractional_count} values with fractional parts."
                )
                return TypeDetectionResult(
                    physical_type=PhysicalType.FLOAT,
                    confidence=float(parse_ratio),
                    evidence=evidence
                )
                
        return None
