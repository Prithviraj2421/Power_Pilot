"""
Datetime detector plugin.
"""
import pandas as pd
from app.common.date_parse import parse_dates_robust
from app.intelligence.schema.TypeDetector.base_detector import BaseDetector
from app.models.type_detection_result import TypeDetectionResult
from app.common.enums import PhysicalType
from app.common.constants import DATE_PARSE_THRESHOLD


class DatetimeDetector(BaseDetector):
    """
    Detector for Datetime physical type.
    """
    
    def detect(self, series: pd.Series) -> TypeDetectionResult | None:
        """
        Detect if the series is of Datetime physical type.
        
        Args:
            series (pd.Series): The pandas Series to analyze.
            
        Returns:
            TypeDetectionResult | None: The detection result if matched, else None.
        """
        valid_series = series.dropna()
        if valid_series.empty:
            return None
            
        # Case 1: Native datetime64 dtype
        if pd.api.types.is_datetime64_any_dtype(valid_series):
            return TypeDetectionResult(
                physical_type=PhysicalType.DATETIME,
                confidence=1.0,
                evidence=(f"Native datetime dtype '{valid_series.dtype}' detected.",)
            )
            
        # Case 2: Object or string dtype — attempt datetime parsing
        if not (pd.api.types.is_object_dtype(valid_series)
                or pd.api.types.is_string_dtype(valid_series)):
            return None
            
        # Attempt conversion
        parsed = parse_dates_robust(valid_series, format='mixed')
        valid_count = parsed.notna().sum()
        total_count = len(valid_series)
        parse_ratio = valid_count / total_count if total_count > 0 else 0.0
        
        if parse_ratio >= DATE_PARSE_THRESHOLD:
            return TypeDetectionResult(
                physical_type=PhysicalType.DATETIME,
                confidence=float(parse_ratio),
                evidence=(
                    f"Successfully parsed {valid_count} out of {total_count} non-null values.",
                    f"Parse ratio ({parse_ratio:.2f}) meets or exceeds threshold ({DATE_PARSE_THRESHOLD}).",
                    "Format was inferred during parsing."
                )
            )
            
        return None
