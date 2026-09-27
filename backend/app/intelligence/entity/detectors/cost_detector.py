from typing import Optional

import pandas as pd

from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult
from app.common.keyword_match import any_keyword_matches
from app.common.enums import SemanticType, PhysicalType


class CostDetector(BaseEntityDetector):
    """
    Detector for COST semantic type.
    """

    KEYWORDS = {"cost", "expense", "cogs", "unit_cost", "purchase_price", "fee", "spend"}

    def detect(
        self,
        column: ColumnProfile,
        series: Optional[pd.Series] = None,
    ) -> Optional[EntityDetectionResult]:
        """
        Detect if the column represents a Cost entity.
        """
        confidence = 0.0
        evidence = []

        col_name_lower = column.name.lower()
        if any_keyword_matches(col_name_lower, self.KEYWORDS):
            confidence += 0.5
            evidence.append(f"Column name '{column.name}' contains cost keywords.")

        valid_types = {PhysicalType.FLOAT, PhysicalType.INTEGER, PhysicalType.DECIMAL}
        if column.physical_type in valid_types:
            confidence += 0.3
            evidence.append(f"Column physical type is numeric ({column.physical_type.value}).")
        else:
            confidence -= 0.5
            
        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.35:
            return EntityDetectionResult(
                semantic_type=SemanticType.COST,
                confidence=confidence,
                reason="Matches COST criteria based on keywords and numeric properties.",
                evidence=tuple(evidence)
            )

        return None
