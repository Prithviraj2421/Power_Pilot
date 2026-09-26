import re
from typing import Optional

import pandas as pd

from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.models.column_profile import ColumnProfile
from app.models.entity_detection_result import EntityDetectionResult
from app.common.enums import SemanticType, PhysicalType


class CustomerDetector(BaseEntityDetector):
    """
    Detector for CUSTOMER semantic type.
    """

    KEYWORDS = {"customer", "client", "buyer", "cust", "account_name", "email", "phone"}

    def detect(
        self,
        column: ColumnProfile,
        series: Optional[pd.Series] = None,
    ) -> Optional[EntityDetectionResult]:
        """
        Detect if the column represents a Customer entity.
        """
        confidence = 0.0
        evidence = []

        col_name_lower = column.name.lower()
        has_keyword = any(kw in col_name_lower for kw in self.KEYWORDS)

        if has_keyword:
            confidence += 0.4
            evidence.append(f"Column name '{column.name}' contains customer keywords.")

        is_text_type = column.physical_type in (PhysicalType.TEXT, PhysicalType.CATEGORICAL)
        if is_text_type and has_keyword:
            confidence += 0.2
            evidence.append("Column is categorical/text and contains customer keywords.")

        if is_text_type and column.sample_values:
            email_pattern = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
            phone_pattern = re.compile(r"^\+?[\d\s\-\(\)]+$")
            
            match_count = 0
            for val in column.sample_values:
                if isinstance(val, str):
                    if email_pattern.match(val) or phone_pattern.match(val):
                        match_count += 1
                        
            if match_count > 0:
                confidence += 0.4
                evidence.append("Sample values look like emails or phone numbers.")

        confidence = round(max(0.0, min(1.0, confidence)), 4)

        if confidence >= 0.35:
            return EntityDetectionResult(
                semantic_type=SemanticType.CUSTOMER,
                confidence=confidence,
                reason="Matches CUSTOMER criteria based on heuristics.",
                evidence=tuple(evidence)
            )

        return None
