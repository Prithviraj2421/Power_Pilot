"""
Text detector plugin.
"""
import pandas as pd
from app.intelligence.schema.TypeDetector.base_detector import BaseDetector
from app.models.type_detection_result import TypeDetectionResult
from app.common.enums import PhysicalType


class TextDetector(BaseDetector):
    """
    Fallback detector for Text physical type.
    """
    _BASE_CONFIDENCE = 0.5
    
    def detect(self, series: pd.Series) -> TypeDetectionResult | None:
        """
        Detect if the series is of Text physical type (fallback).
        
        Args:
            series (pd.Series): The pandas Series to analyze.
            
        Returns:
            TypeDetectionResult | None: The detection result if matched, else None.
        """
        if not (pd.api.types.is_object_dtype(series)
                or pd.api.types.is_string_dtype(series)):
            return None
            
        valid_series = series.dropna()
        if valid_series.empty:
            return None
            
        total_count = len(valid_series)
        unique_count = valid_series.nunique()
        cardinality_ratio = unique_count / total_count if total_count > 0 else 0.0
        
        # Calculate average string length
        str_series = valid_series.astype(str)
        avg_length = str_series.str.len().mean()
        
        confidence = self._BASE_CONFIDENCE
        if avg_length > 50:
            confidence = 0.7
            
        if cardinality_ratio > 0.5:
            confidence += 0.1
            
        confidence = min(0.9, confidence)
        
        evidence = (
            f"Matched fallback text detector for object dtype '{series.dtype}'.",
            f"Average string length is {avg_length:.2f} characters.",
            f"Cardinality ratio is {cardinality_ratio:.4f}.",
            f"Evaluated {total_count} non-null samples."
        )
        
        return TypeDetectionResult(
            physical_type=PhysicalType.TEXT,
            confidence=float(confidence),
            evidence=evidence
        )
