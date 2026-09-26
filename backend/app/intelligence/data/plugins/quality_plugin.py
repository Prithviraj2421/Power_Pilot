from typing import Any, Optional

import numpy as np
import pandas as pd

from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import QualityReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class DataQualityPlugin(BaseDataIntelligencePlugin):
    """
    Computes data quality metrics including null rates, duplicate rows count, and validity.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> QualityReport:
        if df.empty:
            return QualityReport(
                overall_score=0.0,
                completeness_score=0.0,
                uniqueness_score=0.0,
                validity_score=0.0,
                total_issues=0,
                issues=(),
                evidence=(),
            )

        total_rows = len(df)
        total_cells = df.size

        # Completeness
        null_count = int(df.isnull().sum().sum())
        completeness_score = round(float((1.0 - (null_count / total_cells)) * 100.0 if total_cells > 0 else 100.0), 2)

        # Uniqueness
        duplicate_rows = int(df.duplicated().sum())
        uniqueness_score = round(float((1.0 - (duplicate_rows / total_rows)) * 100.0 if total_rows > 0 else 100.0), 2)

        # Validity (checking for infinite values in numeric columns)
        inf_count = 0
        for col in df.select_dtypes(include=[np.number]).columns:
            inf_count += int(np.isinf(df[col]).sum())

        validity_score = round(float((1.0 - (inf_count / total_cells)) * 100.0 if total_cells > 0 else 100.0), 2)

        overall_score = round((completeness_score + uniqueness_score + validity_score) / 3.0, 2)

        issues = []
        if null_count > 0:
            issues.append(f"Found {null_count} missing values across dataset.")
        if duplicate_rows > 0:
            issues.append(f"Found {duplicate_rows} duplicate rows.")
        if inf_count > 0:
            issues.append(f"Found {inf_count} infinite numeric values.")

        evidence = (
            f"Completeness Score: {completeness_score:.1f}% ({null_count} null cells)",
            f"Uniqueness Score: {uniqueness_score:.1f}% ({duplicate_rows} duplicate rows)",
            f"Validity Score: {validity_score:.1f}% ({inf_count} infinite values)",
        )

        return QualityReport(
            overall_score=overall_score,
            completeness_score=completeness_score,
            uniqueness_score=uniqueness_score,
            validity_score=validity_score,
            total_issues=len(issues),
            issues=tuple(issues),
            evidence=evidence,
        )
