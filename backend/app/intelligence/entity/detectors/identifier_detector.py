from typing import Optional

import pandas as pd

from app.common.enums import SemanticType
from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult


class IdentifierDetector(BaseEntityDetector):
    """
    Plugin for detecting the IDENTIFIER semantic type.
    """

    KEYWORDS = {"id", "uuid", "pk", "key", "code", "number", "no"}

    def detect(
        self,
        column: ColumnProfile,
        series: Optional[pd.Series] = None,
    ) -> Optional[EntityDetectionResult]:
        """
        Detect if the given column represents an identifier (e.g., primary key, UUID).
        """
        confidence = 0.0
        evidence = []

        if column.identifier:
            confidence += 0.8
            evidence.append("Schema Analyzer marked column as identifier.")

        col_name_lower = column.name.lower()
        if col_name_lower in self.KEYWORDS or any(col_name_lower.endswith(f"_{kw}") for kw in self.KEYWORDS):
            confidence += 0.5
            evidence.append(f"Column name '{column.name}' matches identifier pattern.")
        elif any(kw in col_name_lower for kw in self.KEYWORDS):
            confidence += 0.3
            evidence.append(f"Column name '{column.name}' contains identifier keywords.")

        if column.unique:
            confidence += 0.2
            evidence.append("Column values are 100% unique.")

        confidence = round(max(0.0, min(1.0, confidence)), 4)

        if confidence >= 0.35:
            return EntityDetectionResult(
                semantic_type=SemanticType.IDENTIFIER,
                confidence=confidence,
                reason="Matches IDENTIFIER criteria based on schema profile and naming.",
                evidence=tuple(evidence),
            )

        return None
