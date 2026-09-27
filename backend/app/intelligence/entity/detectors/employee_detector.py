from typing import Optional

import pandas as pd

from app.common.enums import PhysicalType, SemanticType
from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult
from app.common.keyword_match import any_keyword_matches


class EmployeeDetector(BaseEntityDetector):
    """
    Plugin for detecting the EMPLOYEE semantic type.
    """

    KEYWORDS = {"employee", "emp", "staff", "manager", "agent", "rep", "salesperson", "worker"}

    def detect(
        self,
        column: ColumnProfile,
        series: Optional[pd.Series] = None,
    ) -> Optional[EntityDetectionResult]:
        """
        Detect if the given column represents an employee entity.
        """
        confidence = 0.0
        evidence = []

        col_name_lower = column.name.lower()

        if any_keyword_matches(col_name_lower, self.KEYWORDS):
            confidence += 0.5
            evidence.append(f"Column name '{column.name}' contains employee keywords.")

        if column.physical_type in (PhysicalType.TEXT, PhysicalType.CATEGORICAL, PhysicalType.INTEGER):
            confidence += 0.2
            evidence.append("Physical type is compatible with employee IDs or names.")

        confidence = round(max(0.0, min(1.0, confidence)), 4)

        if confidence >= 0.35:
            return EntityDetectionResult(
                semantic_type=SemanticType.EMPLOYEE,
                confidence=confidence,
                reason="Matches EMPLOYEE criteria based on keywords and physical type.",
                evidence=tuple(evidence),
            )

        return None
