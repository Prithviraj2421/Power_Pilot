from typing import Optional

import pandas as pd

from app.common.enums import PhysicalType, SemanticType
from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult


class RegionDetector(BaseEntityDetector):
    """
    Plugin for detecting the REGION semantic type.
    """

    KEYWORDS = {"region", "state", "country", "city", "zip", "postal_code", "territory", "location", "zone", "address"}

    def detect(
        self,
        column: ColumnProfile,
        series: Optional[pd.Series] = None,
    ) -> Optional[EntityDetectionResult]:
        """
        Detect if the given column represents a geographic region.
        """
        confidence = 0.0
        evidence = []

        col_name_lower = column.name.lower()

        if any(kw in col_name_lower for kw in self.KEYWORDS):
            confidence += 0.5
            evidence.append(f"Column name '{column.name}' contains region/geographic keywords.")

        if column.physical_type in (PhysicalType.TEXT, PhysicalType.CATEGORICAL):
            confidence += 0.2
            evidence.append("Physical type is TEXT or CATEGORICAL.")

        confidence = round(max(0.0, min(1.0, confidence)), 4)

        if confidence >= 0.35:
            return EntityDetectionResult(
                semantic_type=SemanticType.REGION,
                confidence=confidence,
                reason="Matches REGION criteria based on keywords and physical type.",
                evidence=tuple(evidence),
            )

        return None
