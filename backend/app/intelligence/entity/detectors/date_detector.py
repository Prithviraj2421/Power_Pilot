from typing import Optional

import pandas as pd

from app.common.enums import PhysicalType, SemanticType
from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult


class DateDetector(BaseEntityDetector):
    """
    Plugin for detecting the DATE semantic type.
    """

    KEYWORDS = {"date", "timestamp", "time", "created_at", "updated_at", "dob", "hired_at", "order_date"}

    def detect(
        self,
        column: ColumnProfile,
        series: Optional[pd.Series] = None,
    ) -> Optional[EntityDetectionResult]:
        """
        Detect if the given column represents a date or timestamp.
        """
        confidence = 0.0
        evidence = []

        if column.physical_type in (PhysicalType.DATETIME, PhysicalType.DATE):
            confidence += 0.8
            evidence.append(f"Physical type is '{column.physical_type.value}'.")
        elif column.physical_type == PhysicalType.TIME:
            confidence += 0.6
            evidence.append("Physical type is 'time'.")

        col_name_lower = column.name.lower()
        if any(kw in col_name_lower for kw in self.KEYWORDS):
            confidence += 0.4
            evidence.append(f"Column name '{column.name}' contains date keywords.")

        confidence = round(max(0.0, min(1.0, confidence)), 4)

        if confidence >= 0.35:
            return EntityDetectionResult(
                semantic_type=SemanticType.DATE,
                confidence=confidence,
                reason="Matches DATE criteria based on physical type and keywords.",
                evidence=tuple(evidence),
            )

        return None
