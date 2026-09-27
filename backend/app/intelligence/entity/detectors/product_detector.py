import re
from typing import Optional

import pandas as pd

from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult
from app.common.keyword_match import any_keyword_matches
from app.common.enums import SemanticType, PhysicalType


class ProductDetector(BaseEntityDetector):
    """
    Detector for PRODUCT semantic type.
    """

    KEYWORDS = {"product", "item", "sku", "goods", "category", "brand", "model", "merchandise"}

    def detect(
        self,
        column: ColumnProfile,
        series: Optional[pd.Series] = None,
    ) -> Optional[EntityDetectionResult]:
        """
        Detect if the column represents a Product entity.
        """
        confidence = 0.0
        evidence = []

        col_name_lower = column.name.lower()
        if any_keyword_matches(col_name_lower, self.KEYWORDS):
            confidence += 0.5
            evidence.append(f"Column name '{column.name}' contains product keywords.")

        if column.physical_type in (PhysicalType.TEXT, PhysicalType.CATEGORICAL):
            confidence += 0.2
            evidence.append("Column physical type is TEXT or CATEGORICAL.")

        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.35:
            return EntityDetectionResult(
                semantic_type=SemanticType.PRODUCT,
                confidence=confidence,
                reason="Matches PRODUCT criteria based on keywords and physical type.",
                evidence=tuple(evidence)
            )

        return None
