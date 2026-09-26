"""
Category detector plugin.
"""
import pandas as pd
from app.intelligence.schema.TypeDetector.base_detector import BaseDetector
from app.models.type_detection_result import TypeDetectionResult
from app.common.enums import PhysicalType
from app.common.constants import CATEGORY_MAX_CARDINALITY, CATEGORY_MAX_RATIO


class CategoryDetector(BaseDetector):
    """
    Detector for Categorical physical type.
    """
    
    def detect(self, series: pd.Series) -> TypeDetectionResult | None:
        """
        Detect if the series is of Categorical physical type.
        
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
        
        if unique_count <= CATEGORY_MAX_CARDINALITY and cardinality_ratio <= CATEGORY_MAX_RATIO:
            confidence = min(0.95, 1.0 - cardinality_ratio)
            
            top_values = valid_series.value_counts().head(5).index.tolist()
            top_values_str = ", ".join(map(str, top_values))
            
            evidence = (
                f"Unique value count ({unique_count}) <= max allowed ({CATEGORY_MAX_CARDINALITY}).",
                f"Cardinality ratio ({cardinality_ratio:.4f}) <= max allowed ({CATEGORY_MAX_RATIO}).",
                f"Total valid samples evaluated: {total_count}.",
                f"Top 5 frequent values: {top_values_str}."
            )
            
            return TypeDetectionResult(
                physical_type=PhysicalType.CATEGORICAL,
                confidence=float(confidence),
                evidence=evidence
            )
            
        return None
