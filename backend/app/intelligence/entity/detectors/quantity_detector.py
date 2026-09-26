from typing import Optional

import pandas as pd

from app.common.enums import PhysicalType, SemanticType
from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult


class QuantityDetector(BaseEntityDetector):
    """
    Plugin for detecting the QUANTITY semantic type.
    """

    KEYWORDS = {"quantity", "qty", "units", "volume", "count", "items_sold", "pieces"}

    def detect(
        self,
        column: ColumnProfile,
        series: Optional[pd.Series] = None,
    ) -> Optional[EntityDetectionResult]:
        """
        Detect if the given column represents a quantity.
        """
        confidence = 0.0
        evidence = []

        col_name_lower = column.name.lower()

        if any(kw in col_name_lower for kw in self.KEYWORDS):
            confidence += 0.5
            evidence.append(f"Column name '{column.name}' contains quantity keywords.")

        valid_types = {PhysicalType.INTEGER, PhysicalType.FLOAT, PhysicalType.DECIMAL}
        if column.physical_type in valid_types:
            confidence += 0.3
            evidence.append(f"Column physical type is numeric ({column.physical_type.value}).")

            if column.sample_values:
                pos_samples = [v for v in column.sample_values if isinstance(v, (int, float)) and v >= 0]
                if pos_samples:
                    confidence += 0.2
                    evidence.append("Sample values are non-negative numeric quantities.")
        else:
            confidence -= 0.3

        confidence = round(max(0.0, min(1.0, confidence)), 4)

        if confidence >= 0.35:
            return EntityDetectionResult(
                semantic_type=SemanticType.QUANTITY,
                confidence=confidence,
                reason="Matches QUANTITY criteria based on keywords and numeric properties.",
                evidence=tuple(evidence),
            )

        return None
