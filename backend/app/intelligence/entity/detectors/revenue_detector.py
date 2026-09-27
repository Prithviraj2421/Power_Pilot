from typing import Optional

import pandas as pd

from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult
from app.common.keyword_match import any_keyword_matches
from app.common.enums import SemanticType, PhysicalType


class RevenueDetector(BaseEntityDetector):
    """
    Detector for REVENUE semantic type.
    """

    KEYWORDS = {"revenue", "sales", "turnover", "gross", "income", "total_amount", "amount", "price", "billing"}

    def detect(
        self,
        column: ColumnProfile,
        series: Optional[pd.Series] = None,
    ) -> Optional[EntityDetectionResult]:
        """
        Detect if the column represents a Revenue entity.
        """
        confidence = 0.0
        evidence = []

        col_name_lower = column.name.lower()
        if any_keyword_matches(col_name_lower, self.KEYWORDS):
            confidence += 0.5
            evidence.append(f"Column name '{column.name}' contains revenue keywords.")

        valid_types = {PhysicalType.FLOAT, PhysicalType.INTEGER, PhysicalType.DECIMAL}
        if column.physical_type in valid_types:
            confidence += 0.3
            evidence.append(f"Column physical type is numeric ({column.physical_type.value}).")
            
            if column.sample_values:
                positive_count = sum(1 for v in column.sample_values if isinstance(v, (int, float)) and v > 0)
                if positive_count > 0:
                    confidence += 0.2
                    evidence.append("Contains positive numeric values typical for revenue.")
        else:
            confidence -= 0.5
            
        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.35:
            return EntityDetectionResult(
                semantic_type=SemanticType.REVENUE,
                confidence=confidence,
                reason="Matches REVENUE criteria based on keywords and numeric properties.",
                evidence=tuple(evidence)
            )

        return None
